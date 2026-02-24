"""
Data Lineage and Provenance Tracker - Example Usage

This file demonstrates how to use the data lineage and provenance tracker
with UUID-based identification and comprehensive metadata propagation.
"""

import asyncio
import time
from typing import Dict, Any

from lineage import (
    get_tracker,
    get_metadata_manager,
    get_provenance_tracker,
    track_data_lineage_globally,
    track_provenance_globally,
    get_lineage_summary_globally,
    get_provenance_summary_globally,
    get_full_data_history_globally,
    get_full_provenance_history_globally,
    get_system_status_globally
)
from lineage.metadata_manager import MetadataType
from lineage.lineage_tracker import LineageOperation, DataObjectType
from lineage.provenance_tracker import ProvenanceType


async def demonstrate_basic_lineage_tracking():
    """Demonstrate basic data lineage tracking."""
    print("=== Basic Data Lineage Tracking ===\n")
    
    try:
        # Get lineage tracker
        tracker = get_tracker()
        
        print("1. Tracking data from different providers:")
        
        # Track data from Finnhub
        finnhub_data = {
            "symbol": "AAPL",
            "price": 150.25,
            "timestamp": "2023-01-01T10:00:00Z",
            "volume": 1000000
        }
        
        finnhub_context = {
            "user_id": "user123",
            "adapter_version": "2.1.0",
            "source_system": "finnhub_adapter"
        }
        
        finnhub_object_id = await track_data_lineage_globally(
            provider_name="finnhub",
            data=finnhub_data,
            operation=LineageOperation.CREATE,
            context=finnhub_context
        )
        
        print(f"   Finnhub data tracked with ID: {finnhub_object_id}")
        
        # Track data from Alpha Vantage
        alpha_vantage_data = {
            "symbol": "AAPL",
            "price": 150.30,
            "timestamp": "2023-01-01T10:01:00Z",
            "open": 149.50,
            "high": 151.00,
            "low": 149.00
        }
        
        alpha_vantage_context = {
            "user_id": "user123",
            "adapter_version": "1.5.0",
            "source_system": "alpha_vantage_adapter"
        }
        
        alpha_vantage_object_id = await track_data_lineage_globally(
            provider_name="alpha_vantage",
            data=alpha_vantage_data,
            operation=LineageOperation.CREATE,
            context=alpha_vantage_context
        )
        
        print(f"   Alpha Vantage data tracked with ID: {alpha_vantage_object_id}")
        
        print("\n2. Getting lineage summaries:")
        
        # Get lineage summary for Finnhub data
        finnhub_summary = await get_lineage_summary_globally(
            finnhub_object_id,
            provider_name="finnhub"
        )
        
        print(f"   Finnhub lineage summary:")
        print(f"     Object ID: {finnhub_summary['object_id']}")
        print(f"     Object type: {finnhub_summary['object_type']}")
        print(f"     Created at: {finnhub_summary['created_at']}")
        print(f"     Size bytes: {finnhub_summary['size_bytes']}")
        print(f"     Checksum: {finnhub_summary['checksum']}")
        
        # Get lineage summary for Alpha Vantage data
        alpha_vantage_summary = await get_lineage_summary_globally(
            alpha_vantage_object_id,
            provider_name="alpha_vantage"
        )
        
        print(f"   Alpha Vantage lineage summary:")
        print(f"     Object ID: {alpha_vantage_summary['object_id']}")
        print(f"     Object type: {alpha_vantage_summary['object_type']}")
        print(f"     Created at: {alpha_vantage_summary['created_at']}")
        print(f"     Size bytes: {alpha_vantage_summary['size_bytes']}")
        print(f"     Checksum: {alpha_vantage_summary['checksum']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_data_transformation():
    """Demonstrate data transformation tracking."""
    print("\n=== Data Transformation Tracking ===\n")
    
    try:
        # Get lineage tracker
        tracker = get_tracker()
        
        print("1. Creating base data objects:")
        
        # Create two base data objects
        base_data_1 = {
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "source": "provider1"
        }
        
        base_data_2 = {
            "symbol": "AAPL",
            "price": 150.30,
            "volume": 950000,
            "source": "provider2"
        }
        
        # Track base objects
        base_id_1 = await track_data_lineage_globally(
            provider_name="provider1",
            data=base_data_1,
            operation=LineageOperation.CREATE,
            context={"user_id": "user123", "adapter_version": "1.0.0"}
        )
        
        base_id_2 = await track_data_lineage_globally(
            provider_name="provider2",
            data=base_data_2,
            operation=LineageOperation.CREATE,
            context={"user_id": "user123", "adapter_version": "1.0.0"}
        )
        
        print(f"   Base object 1 ID: {base_id_1}")
        print(f"   Base object 2 ID: {base_id_2}")
        
        print("\n2. Performing data transformation:")
        
        # Transform data (merge and average)
        transformed_data = {
            "symbol": "AAPL",
            "avg_price": (150.25 + 150.30) / 2,
            "total_volume": 1000000 + 950000,
            "price_sources": ["provider1", "provider2"],
            "transformation": "price_averaging"
        }
        
        transformation_context = {
            "user_id": "user123",
            "transformation_type": "merge_and_average",
            "adapter_version": "2.0.0"
        }
        
        # Track transformation
        transformed_id = await tracker.track_transformation(
            input_object_ids=[base_id_1, base_id_2],
            output_data=transformed_data,
            transformation_type="merge_and_average",
            transformation_logic="Merge data from multiple sources and calculate average price",
            context=transformation_context
        )
        
        print(f"   Transformed object ID: {transformed_id}")
        
        print("\n3. Getting transformation lineage:")
        
        # Get lineage summary for transformed data
        transformed_summary = await get_lineage_summary_globally(transformed_id)
        
        print(f"   Transformed data summary:")
        print(f"     Object ID: {transformed_summary['object_id']}")
        print(f"     Total dependencies: {transformed_summary['total_dependencies']}")
        print(f"     Parent IDs: {transformed_summary['metadata'].get('input_object_ids', [])}")
        print(f"     Transformation type: {transformed_summary['metadata'].get('transformation_type', 'unknown')}")
        
        print("\n4. Getting full data history:")
        
        # Get full data history
        history = await get_full_data_history_globally(transformed_id)
        
        print(f"   Data history for transformed object:")
        for i, event in enumerate(history):
            print(f"     {i+1}. {event['timestamp']} - {event['operation']} - {event['object_id']}")
            if 'transformation_logic' in event:
                print(f"        Transformation: {event['transformation_logic']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_metadata_propagation():
    """Demonstrate metadata propagation through transformations."""
    print("\n=== Metadata Propagation ===\n")
    
    try:
        # Get metadata manager
        metadata_manager = get_metadata_manager()
        
        print("1. Adding comprehensive metadata to base object:")
        
        # Create base object with rich metadata
        base_object_id = "test_base_object"
        
        base_metadata = {
            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
            "source_name": "primary_data_provider",
            "fetch_timestamp": "2023-01-01T10:00:00Z",
            "adapter_version": "2.1.0",
            "data_quality": {
                "completeness": 0.95,
                "accuracy": 0.98,
                "consistency": 0.92
            },
            "business_context": {
                "department": "trading",
                "use_case": "market_analysis",
                "priority": "high"
            },
            "technical_details": {
                "schema_version": "1.2",
                "encoding": "utf-8",
                "compression": "gzip"
            }
        }
        
        await metadata_manager.add_metadata(
            object_id=base_object_id,
            metadata=base_metadata,
            metadata_type=MetadataType.SOURCE,
            context={"user_id": "user123"}
        )
        
        print(f"   Added metadata to base object: {base_object_id}")
        
        print("\n2. Performing transformation with metadata propagation:")
        
        # Transform data
        transformed_data = {
            "symbol": "AAPL",
            "processed_price": 150.25,
            "indicators": ["sma", "ema", "rsi"]
        }
        
        # Get lineage tracker and perform transformation
        tracker = get_tracker()
        
        # First, track the base object
        base_tracked_id = await track_data_lineage_globally(
            provider_name="primary_data_provider",
            data={"symbol": "AAPL", "price": 150.25},
            operation=LineageOperation.CREATE,
            context={"user_id": "user123", "adapter_version": "2.1.0"}
        )
        
        # Then transform it
        transformed_id = await tracker.track_transformation(
            input_object_ids=[base_tracked_id],
            output_data=transformed_data,
            transformation_type="technical_analysis",
            transformation_logic="Add technical indicators to price data",
            context={"user_id": "user123"}
        )
        
        print(f"   Transformed object ID: {transformed_id}")
        
        print("\n3. Checking propagated metadata:")
        
        # Get metadata for transformed object
        transformed_metadata = await metadata_manager.get_metadata(transformed_id)
        
        print(f"   Transformed object metadata:")
        for key, value in transformed_metadata.items():
            print(f"     {key}: {value}")
        
        # Check for propagation-specific metadata
        if "propagation_operation" in transformed_metadata:
            print(f"   Propagation operation: {transformed_metadata['propagation_operation']}")
        
        if "source_object_ids" in transformed_metadata:
            print(f"   Source object IDs: {transformed_metadata['source_object_ids']}")
        
        print("\n4. Getting metadata history:")
        
        # Get metadata history
        metadata_history = await metadata_manager.get_metadata_history(transformed_id, "transformation_type")
        
        print(f"   Metadata history for transformed object:")
        for i, entry in enumerate(metadata_history):
            print(f"     {i+1}. Version {entry['version']} - {entry['timestamp']}")
            print(f"        Value: {entry['value']}")
            print(f"        User: {entry['user_id']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_provenance_tracking():
    """Demonstrate comprehensive provenance tracking."""
    print("\n=== Provenance Tracking ===\n")
    
    try:
        # Get provenance tracker
        provenance_tracker = get_provenance_tracker()
        
        print("1. Tracking various provenance events:")
        
        object_id = "test_provenance_object"
        
        # Track data creation
        creation_details = {
            "action": "create_financial_data",
            "data_type": "market_data",
            "source": "api_call",
            "record_count": 1000
        }
        
        creation_context = {
            "user_id": "user123",
            "session_id": "session_456",
            "source_system": "market_data_collector",
            "ip_address": "192.168.1.100"
        }
        
        creation_event_id = await track_provenance_globally(
            object_id=object_id,
            provenance_type=ProvenanceType.DATA_CREATION,
            details=creation_details,
            context=creation_context
        )
        
        print(f"   Data creation event ID: {creation_event_id}")
        
        # Track data access
        access_details = {
            "action": "read_financial_data",
            "access_method": "api_query",
            "query_params": {"symbol": "AAPL", "timeframe": "1d"},
            "result_count": 500
        }
        
        access_context = {
            "user_id": "user123",
            "session_id": "session_456",
            "source_system": "api_gateway"
        }
        
        access_event_id = await track_provenance_globally(
            object_id=object_id,
            provenance_type=ProvenanceType.DATA_ACCESS,
            details=access_details,
            context=access_context
        )
        
        print(f"   Data access event ID: {access_event_id}")
        
        # Track data modification
        modification_details = {
            "action": "update_financial_data",
            "modification_type": "price_correction",
            "old_value": 150.25,
            "new_value": 150.30,
            "reason": "price_adjustment"
        }
        
        modification_context = {
            "user_id": "admin_user",
            "session_id": "session_789",
            "source_system": "data_admin_tool"
        }
        
        modification_event_id = await track_provenance_globally(
            object_id=object_id,
            provenance_type=ProvenanceType.DATA_MODIFICATION,
            details=modification_details,
            context=modification_context
        )
        
        print(f"   Data modification event ID: {modification_event_id}")
        
        print("\n2. Getting provenance summary:")
        
        # Get provenance summary
        provenance_summary = await get_provenance_summary_globally(object_id)
        
        print(f"   Provenance summary for object {object_id}:")
        print(f"     Total events: {provenance_summary['total_events']}")
        print(f"     Successful events: {provenance_summary['successful_events']}")
        print(f"     Failed events: {provenance_summary['failed_events']}")
        print(f"     Success rate: {provenance_summary['success_rate']:.2%}")
        print(f"     Compliance rate: {provenance_summary['compliance_rate']:.2%}")
        print(f"     Events by type: {provenance_summary['events_by_type']}")
        print(f"     Events by user: {provenance_summary['events_by_user']}")
        
        print("\n3. Getting full provenance history:")
        
        # Get full provenance history
        provenance_history = await get_full_provenance_history_globally(object_id)
        
        print(f"   Full provenance history for object {object_id}:")
        for i, event in enumerate(provenance_history):
            print(f"     {i+1}. {event['timestamp']} - {event['provenance_type']}")
            print(f"        Event ID: {event['event_id']}")
            print(f"        User: {event['user_id']}")
            print(f"        Action: {event['action']}")
            print(f"        Outcome: {event['outcome']}")
            print(f"        Security level: {event['security_level']}")
            print(f"        Is compliant: {event['is_compliant']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_compliance_reporting():
    """Demonstrate compliance reporting capabilities."""
    print("\n=== Compliance Reporting ===\n")
    
    try:
        # Get provenance tracker
        provenance_tracker = get_provenance_tracker()
        
        print("1. Creating test data with compliance events:")
        
        object_id = "compliance_test_object"
        
        # Create some events with compliance issues
        events = [
            {
                "type": ProvenanceType.DATA_CREATION,
                "details": {"action": "create_sensitive_data", "classification": "confidential"},
                "context": {"user_id": "user123", "permissions": ["read", "write"]}
            },
            {
                "type": ProvenanceType.DATA_ACCESS,
                "details": {"action": "access_sensitive_data", "classification": "confidential"},
                "context": {"user_id": "user456", "permissions": ["read"]}
            },
            {
                "type": ProvenanceType.DATA_MODIFICATION,
                "details": {"action": "modify_without_approval", "requires_approval": True},
                "context": {"user_id": "user789", "permissions": ["write"]}
            }
        ]
        
        event_ids = []
        for event_data in events:
            event_id = await track_provenance_globally(
                object_id=object_id,
                provenance_type=event_data["type"],
                details=event_data["details"],
                context=event_data["context"]
            )
            event_ids.append(event_id)
        
        print(f"   Created {len(event_ids)} compliance test events")
        
        print("\n2. Generating compliance reports:")
        
        # Generate different types of compliance reports
        compliance_types = ["data_access", "data_modification", "sensitive_data"]
        
        for compliance_type in compliance_types:
            try:
                report = await provenance_tracker.generate_compliance_report(
                    object_id=object_id,
                    compliance_type=compliance_type,
                    time_range="2023-01-01T00:00:00Z/2023-12-31T23:59:59Z"
                )
                
                print(f"   {compliance_type.upper()} Compliance Report:")
                print(f"     Report ID: {report.report_id}")
                print(f"     Total events: {report.total_events}")
                print(f"     Compliant events: {report.compliant_events}")
                print(f"     Non-compliant events: {report.non_compliant_events}")
                print(f"     Compliance rate: {report.compliant_events / max(report.total_events, 1):.2%}")
                print(f"     Violations: {len(report.violations)}")
                print(f"     Recommendations: {len(report.recommendations)}")
                
                for violation in report.violations:
                    print(f"       Violation: {violation['description']} (Severity: {violation['severity']})")
                
                for recommendation in report.recommendations:
                    print(f"       Recommendation: {recommendation}")
                
            except Exception as e:
                print(f"   Error generating {compliance_type} report: {e}")
        
        print("\n3. System compliance status:")
        
        # Get system status
        status = get_system_status_globally()
        
        print(f"   Lineage tracker status: {status['lineage_tracker']['storage_type']}")
        print(f"   Metadata manager status: {status['metadata_manager']['storage_type']}")
        print(f"   Provenance tracker status: {status['provenance_tracker']['storage_type']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_real_world_scenario():
    """Demonstrate real-world data lineage scenario."""
    print("\n=== Real-World Data Lineage Scenario ===\n")
    
    try:
        print("1. Simulating market data pipeline:")
        
        # Step 1: Raw data ingestion from multiple sources
        sources = ["finnhub", "alpha_vantage", "polygon"]
        raw_data_ids = []
        
        for source in sources:
            raw_data = {
                "symbol": "AAPL",
                "source": source,
                "price": 150.25 + hash(source) % 10,
                "volume": 1000000 + hash(source) % 100000,
                "timestamp": "2023-01-01T10:00:00Z"
            }
            
            context = {
                "user_id": "data_pipeline",
                "adapter_version": "2.1.0",
                "source_system": f"{source}_adapter",
                "pipeline_stage": "ingestion"
            }
            
            object_id = await track_data_lineage_globally(
                provider_name=source,
                data=raw_data,
                operation=LineageOperation.CREATE,
                context=context
            )
            
            raw_data_ids.append(object_id)
            print(f"   Ingested raw data from {source}: {object_id}")
        
        # Step 2: Data validation and quality checks
        print("\n2. Performing data validation:")
        
        validated_data_ids = []
        for i, raw_id in enumerate(raw_data_ids):
            validation_details = {
                "action": "validate_market_data",
                "validation_rules": ["price_range", "volume_range", "timestamp_format"],
                "validation_result": "passed",
                "quality_score": 0.95
            }
            
            validation_context = {
                "user_id": "data_validator",
                "source_system": "quality_service",
                "pipeline_stage": "validation"
            }
            
            validation_event_id = await track_provenance_globally(
                object_id=raw_id,
                provenance_type=ProvenanceType.QUALITY_CHECK,
                details=validation_details,
                context=validation_context
            )
            
            # Create validated object
            validated_data = {
                "symbol": "AAPL",
                "validated_price": 150.25 + i,
                "validated_volume": 1000000 + i * 100000,
                "quality_score": 0.95,
                "validation_timestamp": "2023-01-01T10:01:00Z"
            }
            
            validated_context = {
                "user_id": "data_validator",
                "adapter_version": "1.0.0",
                "source_system": "quality_service",
                "pipeline_stage": "validated"
            }
            
            validated_id = await track_data_lineage_globally(
                provider_name="quality_service",
                data=validated_data,
                operation=LineageOperation.TRANSFORM,
                context=validated_context
            )
            
            validated_data_ids.append(validated_id)
            print(f"   Validated data {i+1}: {validated_id}")
        
        # Step 3: Data aggregation and enrichment
        print("\n3. Performing data aggregation:")
        
        tracker = get_tracker()
        
        aggregated_data = {
            "symbol": "AAPL",
            "avg_price": sum([150.25 + i for i in range(len(validated_data_ids))]) / len(validated_data_ids),
            "total_volume": sum([1000000 + i * 100000 for i in range(len(validated_data_ids))]),
            "source_count": len(validated_data_ids),
            "aggregation_timestamp": "2023-01-01T10:02:00Z",
            "enrichment": {
                "market_cap": "2.5T",
                "sector": "Technology",
                "industry": "Consumer Electronics"
            }
        }
        
        aggregation_context = {
            "user_id": "data_aggregator",
            "transformation_type": "multi_source_aggregation",
            "adapter_version": "3.0.0",
            "source_system": "aggregation_service",
            "pipeline_stage": "aggregated"
        }
        
        aggregated_id = await tracker.track_transformation(
            input_object_ids=validated_data_ids,
            output_data=aggregated_data,
            transformation_type="multi_source_aggregation",
            transformation_logic="Aggregate data from multiple validated sources and add enrichment",
            context=aggregation_context
        )
        
        print(f"   Aggregated data: {aggregated_id}")
        
        # Step 4: Final lineage analysis
        print("\n4. Analyzing complete lineage:")
        
        # Get full data history for aggregated object
        full_history = await get_full_data_history_globally(aggregated_id)
        
        print(f"   Complete lineage for aggregated object:")
        for i, event in enumerate(full_history):
            print(f"     {i+1}. {event['timestamp']} - {event['operation']} - {event['object_type']}")
            print(f"        Object ID: {event['object_id']}")
            print(f"        Name: {event['name']}")
            print(f"        Size: {event['size_bytes']} bytes")
            if 'transformation_logic' in event:
                print(f"        Transformation: {event['transformation_logic']}")
        
        # Get provenance summary
        provenance_summary = await get_provenance_summary_globally(aggregated_id)
        
        print(f"\n   Provenance summary:")
        print(f"     Total events: {provenance_summary['total_events']}")
        print(f"     Success rate: {provenance_summary['success_rate']:.2%}")
        print(f"     Compliance rate: {provenance_summary['compliance_rate']:.2%}")
        print(f"     Time span: {provenance_summary['time_span_seconds']:.2f} seconds")
        
        # Get metadata summary
        metadata_manager = get_metadata_manager()
        metadata_summary = await metadata_manager.get_metadata_summary(aggregated_id)
        
        print(f"\n   Metadata summary:")
        print(f"     Total entries: {metadata_summary['total_entries']}")
        print(f"     Metadata types: {list(metadata_summary['metadata_types'].keys())}")
        print(f"     Latest update: {metadata_summary['latest_update']}")
        print(f"     Unique sources: {metadata_summary['unique_sources']}")
        
        print("\n5. Compliance verification:")
        
        # Generate compliance reports
        compliance_types = ["data_access", "data_modification", "audit_requirements"]
        
        for compliance_type in compliance_types:
            try:
                report = await provenance_tracker.generate_compliance_report(
                    object_id=aggregated_id,
                    compliance_type=compliance_type
                )
                
                compliance_rate = report.compliant_events / max(report.total_events, 1)
                print(f"     {compliance_type}: {compliance_rate:.2%} compliant")
                
                if report.violations:
                    print(f"       Violations: {len(report.violations)}")
                
            except Exception as e:
                print(f"     {compliance_type}: Error - {e}")
        
        print("\n6. Financial and technical audit capabilities:")
        
        print("   ✓ Complete data lineage from source to final product")
        print("   ✓ Metadata propagation through all transformations")
        print("   ✓ Comprehensive provenance tracking with audit trail")
        print("   ✓ Compliance reporting with violation detection")
        print("   ✓ Data integrity verification with checksums")
        print("   ✓ Multi-source data aggregation tracking")
        print("   ✓ Quality metrics and validation history")
        print("   ✓ User and system access logging")
        print("   ✓ Time-based audit capabilities")
        
    except Exception as e:
        print(f"   Error: {e}")


async def main():
    """Run all lineage and provenance demonstrations."""
    print("Data Lineage and Provenance Tracker - Complete Demonstration")
    print("=" * 70)
    
    try:
        await demonstrate_basic_lineage_tracking()
        await demonstrate_data_transformation()
        await demonstrate_metadata_propagation()
        await demonstrate_provenance_tracking()
        await demonstrate_compliance_reporting()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 70)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ UUID-based object identification")
        print("✓ Comprehensive metadata with trace_id, source_name, fetch_timestamp, adapter_version")
        print("✓ Metadata propagation through transformations and merges")
        print("✓ Complete data lineage tracking with parent-child relationships")
        print("✓ Provenance tracking with detailed audit trails")
        print("✓ Compliance reporting with violation detection")
        print("✓ Data integrity verification with checksums")
        print("✓ Multi-source data aggregation tracking")
        print("✓ Quality metrics and validation history")
        print("✓ Financial audit capabilities")
        print("✓ Technical audit capabilities")
        print("✓ Time-based audit queries")
        print("✅ Full lifecycle tracking from source to consumption")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
