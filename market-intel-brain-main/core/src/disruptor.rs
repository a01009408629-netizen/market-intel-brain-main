//! LMAX Disruptor-inspired high-performance ring buffer implementation
//! 
//! This module provides a lock-free, single-writer multiple-reader ring buffer
//! based on the LMAX Disruptor pattern for ultra-low latency messaging.

use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};
use std::sync::Arc;
use std::cell::UnsafeCell;
use std::mem::MaybeUninit;
use std::ptr;
use std::time::{Instant, Duration};
use crossbeam::utils::Backoff;
use parking_lot::{Mutex, RwLock};
use std::thread::{self, JoinHandle};
use std::collections::VecDeque;

/// Ring buffer capacity (must be power of 2)
pub const BUFFER_SIZE: usize = 1024 * 1024; // 1M entries
pub const BUFFER_MASK: u64 = (BUFFER_SIZE - 1) as u64;

/// Sequence number for tracking positions
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Sequence(u64);

impl Sequence {
    /// Create new sequence
    pub fn new(value: u64) -> Self {
        Sequence(value)
    }
    
    /// Get raw value
    pub fn value(&self) -> u64 {
        self.0
    }
    
    /// Increment sequence
    pub fn increment(&self, delta: u64) -> Sequence {
        Sequence(self.0 + delta)
    }
    
    /// Get buffer index
    pub fn index(&self, mask: u64) -> usize {
        (self.0 & mask) as usize
    }
}

/// Event wrapper for ring buffer entries
#[derive(Debug)]
pub struct Event<T> {
    /// Event data
    pub data: MaybeUninit<T>,
    /// Event sequence number
    pub sequence: Sequence,
    /// Event timestamp
    pub timestamp: Instant,
    /// Event type identifier
    pub event_type: u32,
    /// Processing flags
    pub flags: u32,
}

impl<T> Event<T> {
    /// Create new event
    pub fn new(data: T, sequence: Sequence, event_type: u32) -> Self {
        Self {
            data: MaybeUninit::new(data),
            sequence,
            timestamp: Instant::now(),
            event_type,
            flags: 0,
        }
    }
    
    /// Get event data (unsafe - assumes initialized)
    pub unsafe fn data(&self) -> &T {
        &*self.data.as_ptr()
    }
    
    /// Get mutable event data (unsafe - assumes initialized)
    pub unsafe fn data_mut(&mut self) -> &mut T {
        &mut *self.data.as_mut_ptr()
    }
    
    /// Take event data (unsafe - assumes initialized)
    pub unsafe fn take_data(self) -> T {
        self.data.assume_init()
    }
}

/// Ring buffer implementation
pub struct RingBuffer<T> {
    /// Buffer storage
    buffer: Box<[UnsafeCell<Event<T>>]>,
    /// Write sequence
    write_sequence: AtomicU64,
    /// Read sequences for each consumer
    read_sequences: Vec<AtomicU64>,
    /// Gating sequences for coordination
    gating_sequences: Vec<Arc<AtomicSequence>>,
    /// Buffer mask for modulo operation
    mask: u64,
    /// Buffer capacity
    capacity: usize,
}

impl<T> RingBuffer<T> {
    /// Create new ring buffer
    pub fn new(num_consumers: usize) -> Self {
        let buffer = (0..BUFFER_SIZE)
            .map(|_| UnsafeCell::new(Event {
                data: MaybeUninit::uninit(),
                sequence: Sequence(0),
                timestamp: Instant::now(),
                event_type: 0,
                flags: 0,
            }))
            .collect::<Vec<_>>()
            .into_boxed_slice();
        
        let read_sequences = (0..num_consumers)
            .map(|_| AtomicU64::new(0))
            .collect();
        
        Self {
            buffer,
            write_sequence: AtomicU64::new(0),
            read_sequences,
            gating_sequences: Vec::new(),
            mask: BUFFER_MASK,
            capacity: BUFFER_SIZE,
        }
    }
    
    /// Add gating sequence
    pub fn add_gating_sequence(&mut self, sequence: Arc<AtomicSequence>) {
        self.gating_sequences.push(sequence);
    }
    
    /// Get next available sequence for writing
    pub fn next_sequence(&self) -> Sequence {
        let current = self.write_sequence.load(Ordering::Acquire);
        let next = Sequence(current + 1);
        
        // Check if we can claim this sequence
        if self.can_claim(next) {
            self.write_sequence.store(next.value(), Ordering::Release);
            next
        } else {
            // Wait for space to become available
            self.wait_for_sequence(next)
        }
    }
    
    /// Check if sequence can be claimed
    fn can_claim(&self, sequence: Sequence) -> bool {
        let wrap_point = sequence.value() - self.capacity as u64;
        
        // Check if any gating sequence would be overtaken
        for gating_seq in &self.gating_sequences {
            let min_sequence = gating_seq.get();
            if wrap_point > min_sequence.value() {
                return false;
            }
        }
        
        true
    }
    
    /// Wait for sequence to become available
    fn wait_for_sequence(&self, sequence: Sequence) -> Sequence {
        let backoff = Backoff::new();
        
        loop {
            if self.can_claim(sequence) {
                self.write_sequence.store(sequence.value(), Ordering::Release);
                return sequence;
            }
            
            backoff.snooze();
        }
    }
    
    /// Publish event to buffer
    pub fn publish(&self, sequence: Sequence, event: Event<T>) {
        let index = sequence.index(self.mask);
        let slot = unsafe { &*self.buffer[index].get() };
        
        // Write event data
        unsafe {
            ptr::write(slot as *const Event<T> as *mut Event<T>, event);
        }
        
        // Update gating sequences
        for gating_seq in &self.gating_sequences {
            gating_seq.set(sequence);
        }
    }
    
    /// Get event for reading
    pub fn get_event(&self, sequence: Sequence) -> &Event<T> {
        let index = sequence.index(self.mask);
        unsafe { &*self.buffer[index].get() }
    }
    
    /// Get consumer sequence
    pub fn get_consumer_sequence(&self, consumer_id: usize) -> Sequence {
        Sequence(self.read_sequences[consumer_id].load(Ordering::Acquire))
    }
    
    /// Set consumer sequence
    pub fn set_consumer_sequence(&self, consumer_id: usize, sequence: Sequence) {
        self.read_sequences[consumer_id].store(sequence.value(), Ordering::Release);
    }
    
    /// Get highest readable sequence
    pub fn get_highest_sequence(&self) -> Sequence {
        let write_seq = Sequence(self.write_sequence.load(Ordering::Acquire));
        
        // Find minimum of all consumer sequences
        let min_consumer = self.read_sequences
            .iter()
            .map(|seq| Sequence(seq.load(Ordering::Acquire)))
            .min()
            .unwrap_or(Sequence(0));
        
        std::cmp::min(write_seq, min_consumer)
    }
}

/// Atomic sequence for coordination
#[derive(Debug)]
pub struct AtomicSequence {
    sequence: AtomicU64,
}

impl AtomicSequence {
    /// Create new atomic sequence
    pub fn new(initial: Sequence) -> Self {
        Self {
            sequence: AtomicU64::new(initial.value()),
        }
    }
    
    /// Get current sequence
    pub fn get(&self) -> Sequence {
        Sequence(self.sequence.load(Ordering::Acquire))
    }
    
    /// Set sequence
    pub fn set(&self, sequence: Sequence) {
        self.sequence.store(sequence.value(), Ordering::Release);
    }
    
    /// Compare and swap
    pub fn compare_and_swap(&self, expected: Sequence, new: Sequence) -> Sequence {
        let result = self.sequence.compare_exchange_weak(
            expected.value(),
            new.value(),
            Ordering::AcqRel,
            Ordering::Acquire,
        );
        
        match result {
            Ok(actual) => Sequence(actual),
            Err(actual) => Sequence(actual),
        }
    }
}

/// Event processor trait
pub trait EventProcessor<T>: Send + Sync {
    /// Process single event
    fn process_event(&mut self, event: &Event<T>) -> Result<(), ProcessError>;
    
    /// Get processor name
    fn name(&self) -> &str;
}

/// Processing errors
#[derive(Debug, thiserror::Error)]
pub enum ProcessError {
    #[error("Processing failed: {0}")]
    ProcessingFailed(String),
    
    #[error("Sequence error: {0}")]
    SequenceError(String),
    
    #[error("System error: {0}")]
    SystemError(String),
}

/// Event handler for processing events
pub struct EventHandler<T> {
    /// Processor implementation
    processor: Box<dyn EventProcessor<T>>,
    /// Current sequence
    sequence: Sequence,
    /// Ring buffer reference
    buffer: Arc<RingBuffer<T>>,
    /// Consumer ID
    consumer_id: usize,
    /// Running flag
    running: Arc<AtomicBool>,
    /// Processing statistics
    stats: ProcessingStats,
}

impl<T> EventHandler<T> {
    /// Create new event handler
    pub fn new(
        processor: Box<dyn EventProcessor<T>>,
        buffer: Arc<RingBuffer<T>>,
        consumer_id: usize,
        running: Arc<AtomicBool>,
    ) -> Self {
        Self {
            processor,
            sequence: Sequence(0),
            buffer,
            consumer_id,
            running,
            stats: ProcessingStats::new(),
        }
    }
    
    /// Start event processing loop
    pub fn start(&mut self) -> JoinHandle<Result<(), ProcessError>> {
        let processor = unsafe { ptr::read(&mut *self.processor) };
        let buffer = Arc::clone(&self.buffer);
        let consumer_id = self.consumer_id;
        let running = Arc::clone(&self.running);
        let mut sequence = self.sequence;
        
        thread::spawn(move || {
            let mut processor = processor;
            let mut stats = ProcessingStats::new();
            
            while running.load(Ordering::Acquire) {
                let next_sequence = buffer.get_consumer_sequence(consumer_id).increment(1);
                let highest_sequence = buffer.get_highest_sequence();
                
                if next_sequence.value() <= highest_sequence.value() {
                    // Process available events
                    for seq in sequence.value()..next_sequence.value() {
                        let event = buffer.get_event(Sequence(seq));
                        
                        match processor.process_event(event) {
                            Ok(()) => {
                                stats.increment_processed();
                            }
                            Err(e) => {
                                stats.increment_errors();
                                return Err(e);
                            }
                        }
                    }
                    
                    sequence = next_sequence;
                    buffer.set_consumer_sequence(consumer_id, sequence);
                } else {
                    // No events available, brief pause
                    thread::yield_now();
                }
            }
            
            Ok(())
        })
    }
    
    /// Get processing statistics
    pub fn get_stats(&self) -> &ProcessingStats {
        &self.stats
    }
}

/// Processing statistics
#[derive(Debug)]
pub struct ProcessingStats {
    /// Events processed
    events_processed: u64,
    /// Errors encountered
    errors: u64,
    /// Processing start time
    start_time: Instant,
    /// Last event time
    last_event_time: Option<Instant>,
}

impl ProcessingStats {
    /// Create new stats
    pub fn new() -> Self {
        Self {
            events_processed: 0,
            errors: 0,
            start_time: Instant::now(),
            last_event_time: None,
        }
    }
    
    /// Increment processed count
    pub fn increment_processed(&mut self) {
        self.events_processed += 1;
        self.last_event_time = Some(Instant::now());
    }
    
    /// Increment error count
    pub fn increment_errors(&mut self) {
        self.errors += 1;
    }
    
    /// Get events processed
    pub fn events_processed(&self) -> u64 {
        self.events_processed
    }
    
    /// Get error count
    pub fn errors(&self) -> u64 {
        self.errors
    }
    
    /// Get processing rate
    pub fn processing_rate(&self) -> f64 {
        let elapsed = self.start_time.elapsed().as_secs_f64();
        if elapsed > 0.0 {
            self.events_processed as f64 / elapsed
        } else {
            0.0
        }
    }
}

/// Disruptor engine main structure
pub struct DisruptorEngine<T> {
    /// Ring buffer
    buffer: Arc<RingBuffer<T>>,
    /// Event handlers
    handlers: Vec<EventHandler<T>>,
    /// Running flag
    running: Arc<AtomicBool>,
    /// Worker threads
    workers: Vec<JoinHandle<Result<(), ProcessError>>>,
    /// Engine statistics
    stats: EngineStats,
}

impl<T> DisruptorEngine<T>
where
    T: Send + Sync + 'static,
{
    /// Create new disruptor engine
    pub fn new(num_consumers: usize) -> Self {
        let buffer = Arc::new(RingBuffer::new(num_consumers));
        let running = Arc::new(AtomicBool::new(false));
        
        Self {
            buffer,
            handlers: Vec::new(),
            running,
            workers: Vec::new(),
            stats: EngineStats::new(),
        }
    }
    
    /// Add event processor
    pub fn add_processor<P>(&mut self, processor: P)
    where
        P: EventProcessor<T> + 'static,
    {
        let gating_sequence = Arc::new(AtomicSequence::new(Sequence(0)));
        self.buffer.add_gating_sequence(gating_sequence);
        
        let handler = EventHandler::new(
            Box::new(processor),
            Arc::clone(&self.buffer),
            self.handlers.len(),
            Arc::clone(&self.running),
        );
        
        self.handlers.push(handler);
    }
    
    /// Start the engine
    pub fn start(&mut self) -> Result<(), ProcessError> {
        if self.running.load(Ordering::Acquire) {
            return Err(ProcessError::SystemError("Engine already running".to_string()));
        }
        
        self.running.store(true, Ordering::Release);
        
        // Start all handlers
        for handler in &mut self.handlers {
            let worker = handler.start();
            self.workers.push(worker);
        }
        
        self.stats.start_time = Some(Instant::now());
        Ok(())
    }
    
    /// Stop the engine
    pub fn stop(&mut self) -> Result<(), ProcessError> {
        if !self.running.load(Ordering::Acquire) {
            return Ok(());
        }
        
        self.running.store(false, Ordering::Release);
        
        // Wait for all workers to finish
        for worker in self.workers.drain(..) {
            worker.join().map_err(|e| {
                ProcessError::SystemError(format!("Worker join failed: {:?}", e))
            })??;
        }
        
        self.stats.stop_time = Some(Instant::now());
        Ok(())
    }
    
    /// Publish event
    pub fn publish(&self, data: T, event_type: u32) -> Result<(), ProcessError> {
        let sequence = self.buffer.next_sequence();
        let event = Event::new(data, sequence, event_type);
        self.buffer.publish(sequence, event);
        
        self.stats.increment_published();
        Ok(())
    }
    
    /// Get engine statistics
    pub fn get_stats(&self) -> &EngineStats {
        &self.stats
    }
    
    /// Get handler statistics
    pub fn get_handler_stats(&self) -> Vec<&ProcessingStats> {
        self.handlers.iter().map(|h| h.get_stats()).collect()
    }
}

/// Engine statistics
#[derive(Debug)]
pub struct EngineStats {
    /// Events published
    events_published: u64,
    /// Engine start time
    start_time: Option<Instant>,
    /// Engine stop time
    stop_time: Option<Instant>,
}

impl EngineStats {
    /// Create new stats
    pub fn new() -> Self {
        Self {
            events_published: 0,
            start_time: None,
            stop_time: None,
        }
    }
    
    /// Increment published count
    pub fn increment_published(&mut self) {
        self.events_published += 1;
    }
    
    /// Get events published
    pub fn events_published(&self) -> u64 {
        self.events_published
    }
    
    /// Get uptime
    pub fn uptime(&self) -> Option<Duration> {
        match (self.start_time, self.stop_time) {
            (Some(start), Some(stop)) => Some(stop.duration_since(start)),
            (Some(start), None) => Some(start.elapsed()),
            _ => None,
        }
    }
    
    /// Get publish rate
    pub fn publish_rate(&self) -> f64 {
        if let Some(start) = self.start_time {
            let elapsed = if let Some(stop) = self.stop_time {
                stop.duration_since(start)
            } else {
                start.elapsed()
            };
            
            if elapsed.as_secs_f64() > 0.0 {
                self.events_published as f64 / elapsed.as_secs_f64()
            } else {
                0.0
            }
        } else {
            0.0
        }
    }
}

/// Builder for disruptor engine
pub struct DisruptorBuilder<T> {
    num_consumers: usize,
    processors: Vec<Box<dyn EventProcessor<T>>>,
}

impl<T> DisruptorBuilder<T>
where
    T: Send + Sync + 'static,
{
    /// Create new builder
    pub fn new() -> Self {
        Self {
            num_consumers: 0,
            processors: Vec::new(),
        }
    }
    
    /// Set number of consumers
    pub fn with_consumers(mut self, count: usize) -> Self {
        self.num_consumers = count;
        self
    }
    
    /// Add processor
    pub fn with_processor<P>(mut self, processor: P) -> Self
    where
        P: EventProcessor<T> + 'static,
    {
        self.processors.push(Box::new(processor));
        self
    }
    
    /// Build engine
    pub fn build(self) -> DisruptorEngine<T> {
        let mut engine = DisruptorEngine::new(self.num_consumers);
        
        for processor in self.processors {
            engine.add_processor(processor);
        }
        
        engine
    }
}

impl<T> Default for DisruptorBuilder<T> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};
    
    #[derive(Debug)]
    struct TestProcessor {
        name: String,
        counter: Arc<AtomicU32>,
    }
    
    impl EventProcessor<String> for TestProcessor {
        fn process_event(&mut self, event: &Event<String>) -> Result<(), ProcessError> {
            let data = unsafe { event.data() };
            println!("Processor {} processing: {}", self.name, data);
            self.counter.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
        
        fn name(&self) -> &str {
            &self.name
        }
    }
    
    #[test]
    fn test_sequence_operations() {
        let seq1 = Sequence::new(10);
        let seq2 = seq1.increment(5);
        
        assert_eq!(seq1.value(), 10);
        assert_eq!(seq2.value(), 15);
        assert_eq!(seq2.index(1023), 15);
    }
    
    #[test]
    fn test_atomic_sequence() {
        let seq = AtomicSequence::new(Sequence(5));
        assert_eq!(seq.get().value(), 5);
        
        seq.set(Sequence(10));
        assert_eq!(seq.get().value(), 10);
    }
    
    #[test]
    fn test_processing_stats() {
        let mut stats = ProcessingStats::new();
        stats.increment_processed();
        stats.increment_processed();
        stats.increment_errors();
        
        assert_eq!(stats.events_processed(), 2);
        assert_eq!(stats.errors(), 1);
        assert!(stats.processing_rate() > 0.0);
    }
    
    #[tokio::test]
    async fn test_disruptor_engine() {
        let counter = Arc::new(AtomicU32::new(0));
        
        let mut engine = DisruptorBuilder::new()
            .with_consumers(3)
            .with_processor(TestProcessor {
                name: "Processor1".to_string(),
                counter: Arc::clone(&counter),
            })
            .with_processor(TestProcessor {
                name: "Processor2".to_string(),
                counter: Arc::clone(&counter),
            })
            .build();
        
        engine.start().unwrap();
        
        // Publish some test events
        for i in 0..100 {
            engine.publish(format!("Test message {}", i), 1).unwrap();
        }
        
        // Give some time for processing
        tokio::time::sleep(Duration::from_millis(100)).await;
        
        engine.stop().unwrap();
        
        // Verify events were processed
        let stats = engine.get_stats();
        assert_eq!(stats.events_published(), 100);
        assert!(stats.publish_rate() > 0.0);
    }
}
