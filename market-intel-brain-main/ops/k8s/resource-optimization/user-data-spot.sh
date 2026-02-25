#!/bin/bash
# User data script for Spot Instances with graceful termination handling
# This script sets up the node to handle SIGTERM signals for graceful shutdown

set -euo pipefail

# Variables
CLUSTER_NAME="${cluster_name}"
COMPONENT="${component}"
SHUTDOWN_GRACE_PERIOD="${shutdown_grace_period:-30}"
LOG_FILE="/var/log/spot-termination.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$COMPONENT] $1" | tee -a "$LOG_FILE"
}

# Function to install AWS CLI and other dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    # Update package lists
    apt-get update
    
    # Install required packages
    apt-get install -y \
        awscli \
        curl \
        jq \
        python3 \
        python3-pip \
        unzip
    
    # Install boto3 for Python
    pip3 install boto3 botocore
    
    log "Dependencies installed successfully"
}

# Function to set up monitoring and logging
setup_monitoring() {
    log "Setting up monitoring and logging..."
    
    # Create log directory
    mkdir -p /var/log/spot-termination
    
    # Set up log rotation
    cat > /etc/logrotate.d/spot-termination << EOF
/var/log/spot-termination.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 root root
}
EOF
    
    log "Monitoring and logging setup completed"
}

# Function to create spot termination handler
create_termination_handler() {
    log "Creating spot termination handler..."
    
    cat > /usr/local/bin/spot-termination-handler.py << 'EOF'
#!/usr/bin/env python3
import boto3
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/spot-termination.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SpotTerminationHandler:
    def __init__(self, cluster_name, namespace, component, grace_period):
        self.cluster_name = cluster_name
        self.namespace = namespace
        self.component = component
        self.grace_period = grace_period
        self.ec2_client = boto3.client('ec2')
        self.eks_client = boto3.client('eks')
        self.k8s_client = None
        self.setup_k8s_client()
        
    def setup_k8s_client(self):
        """Setup Kubernetes client for pod management"""
        try:
            # Get EKS cluster endpoint and CA data
            cluster_info = self.eks_client.describe_cluster(name=self.cluster_name)
            
            # Update kubeconfig
            kubeconfig_path = os.path.expanduser('~/.kube/config')
            os.makedirs(os.path.dirname(kubeconfig_path), exist_ok=True)
            
            # Use AWS CLI to update kubeconfig
            subprocess.run([
                'aws', 'eks', 'update-kubeconfig',
                '--name', self.cluster_name,
                '--region', os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
            ], check=True)
            
            # Setup kubernetes client
            from kubernetes import client, config
            config.load_kube_config()
            self.k8s_client = client.CoreV1Api()
            
            logger.info("Kubernetes client setup completed")
        except Exception as e:
            logger.error(f"Failed to setup Kubernetes client: {e}")
            
    def get_instance_metadata(self):
        """Get EC2 instance metadata"""
        try:
            import urllib.request
            with urllib.request.urlopen('http://169.254.169.254/latest/meta-data/') as response:
                metadata = response.read().decode('utf-8')
                
            # Parse metadata
            metadata_dict = {}
            for line in metadata.split('\n'):
                if line:
                    key = line
                    try:
                        with urllib.request.urlopen(f'http://169.254.169.254/latest/meta-data/{key}') as response:
                            value = response.read().decode('utf-8')
                            metadata_dict[key] = value
                    except:
                        pass
                        
            return metadata_dict
        except Exception as e:
            logger.error(f"Failed to get instance metadata: {e}")
            return {}
            
    def get_node_name(self):
        """Get Kubernetes node name from instance metadata"""
        try:
            metadata = self.get_instance_metadata()
            instance_id = metadata.get('instance-id', '')
            local_hostname = metadata.get('local-hostname', '')
            
            # Try to find node by instance ID label
            if self.k8s_client:
                nodes = self.k8s_client.list_node()
                for node in nodes.items:
                    # Check provider ID
                    if node.spec.provider_id and instance_id in node.spec.provider_id:
                        return node.metadata.name
                    # Check instance ID label
                    if node.metadata.labels and node.metadata.labels.get('aws.amazonaws.com/ec2id') == instance_id:
                        return node.metadata.name
                    # Check hostname
                    if node.metadata.name == local_hostname:
                        return node.metadata.name
                        
            # Fallback to hostname
            return local_hostname
        except Exception as e:
            logger.error(f"Failed to get node name: {e}")
            return os.environ.get('HOSTNAME', 'unknown')
            
    def cordon_node(self, node_name):
        """Cordon the node to prevent new pods from being scheduled"""
        try:
            if self.k8s_client:
                # Get current node
                node = self.k8s_client.read_node(name=node_name)
                
                # Add cordon taint
                if not node.spec.unschedulable:
                    node.spec.unschedulable = True
                    
                    # Add termination taint
                    if not node.spec.taints:
                        node.spec.taints = []
                    
                    termination_taint = client.V1Taint(
                        key="termination",
                        value="spot-termination",
                        effect="NoSchedule"
                    )
                    node.spec.taints.append(termination_taint)
                    
                    # Update node
                    self.k8s_client.patch_node(
                        name=node_name,
                        body=node,
                        patch_strategy="merge"
                    )
                    
                    logger.info(f"Node {node_name} cordoned successfully")
                else:
                    logger.info(f"Node {node_name} already cordoned")
        except Exception as e:
            logger.error(f"Failed to cordon node {node_name}: {e}")
            
    def drain_node(self, node_name):
        """Drain the node to evict pods gracefully"""
        try:
            # Use kubectl drain command
            cmd = [
                'kubectl', 'drain', node_name,
                '--ignore-daemonsets',
                '--delete-emptydir-data',
                '--force',
                '--grace-period', str(self.grace_period),
                '--timeout', str(self.grace_period + 10) + 's'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.grace_period + 15)
            
            if result.returncode == 0:
                logger.info(f"Node {node_name} drained successfully")
            else:
                logger.error(f"Failed to drain node {node_name}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Node {node_name} drain timed out")
        except Exception as e:
            logger.error(f"Failed to drain node {node_name}: {e}")
            
    def handle_termination(self):
        """Handle spot instance termination"""
        logger.info("Spot termination detected, starting graceful shutdown")
        
        # Get node name
        node_name = self.get_node_name()
        logger.info(f"Target node: {node_name}")
        
        # Cordon the node
        self.cordon_node(node_name)
        
        # Wait a bit before draining
        time.sleep(5)
        
        # Drain the node
        self.drain_node(node_name)
        
        # Wait for grace period
        logger.info(f"Waiting for {self.grace_period} seconds grace period")
        time.sleep(self.grace_period)
        
        logger.info("Graceful shutdown completed")
        
    def check_spot_interruption(self):
        """Check for spot instance interruption warning"""
        try:
            # Get instance metadata
            metadata = self.get_instance_metadata()
            instance_id = metadata.get('instance-id', '')
            
            if not instance_id:
                return False
                
            # Check for spot interruption notice
            instance_data = self.ec2_client.describe_instance_status(
                InstanceIds=[instance_id],
                IncludeAllInstances=True
            )
            
            for instance in instance_data.InstanceStatuses:
                if instance.InstanceId == instance_id:
                    # Check for spot interruption warning
                    events = instance.Events or []
                    for event in events:
                        if 'spot-interruption-warning' in event.get('Description', '').lower():
                            logger.info(f"Spot interruption warning detected: {event.get('Description')}")
                            return True
                            
            return False
        except Exception as e:
            logger.error(f"Failed to check spot interruption: {e}")
            return False

def signal_handler(signum, frame):
    """Handle SIGTERM signal"""
    logger.info(f"Received signal {signum}, starting graceful shutdown")
    
    # Get environment variables
    cluster_name = os.environ.get('CLUSTER_NAME', 'market-intel-brain')
    namespace = os.environ.get('NAMESPACE', 'market-intel-brain')
    component = os.environ.get('COMPONENT', 'unknown')
    grace_period = int(os.environ.get('SHUTDOWN_GRACE_PERIOD', '30'))
    
    # Create termination handler
    handler = SpotTerminationHandler(cluster_name, namespace, component, grace_period)
    
    # Handle termination
    handler.handle_termination()
    
    # Exit
    sys.exit(0)

def main():
    """Main function"""
    logger.info("Spot termination handler started")
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get configuration
    cluster_name = os.environ.get('CLUSTER_NAME', 'market-intel-brain')
    namespace = os.environ.get('NAMESPACE', 'market-intel-brain')
    component = os.environ.get('COMPONENT', 'unknown')
    grace_period = int(os.environ.get('SHUTDOWN_GRACE_PERIOD', '30'))
    
    # Create handler
    handler = SpotTerminationHandler(cluster_name, namespace, component, grace_period)
    
    # Monitor for spot interruption
    while True:
        try:
            if handler.check_spot_interruption():
                handler.handle_termination()
                break
                
            # Sleep for 5 seconds before next check
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
EOF
    
    # Make the script executable
    chmod +x /usr/local/bin/spot-termination-handler.py
    
    log "Spot termination handler created successfully"
}

# Function to create systemd service for termination handler
create_termination_service() {
    log "Creating systemd service for termination handler..."
    
    cat > /etc/systemd/system/spot-termination-handler.service << EOF
[Unit]
Description=Spot Instance Termination Handler
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/spot-termination-handler.py
Restart=always
RestartSec=10
User=root
Group=root
Environment=CLUSTER_NAME=${CLUSTER_NAME}
Environment=NAMESPACE=market-intel-brain
Environment=COMPONENT=${COMPONENT}
Environment=SHUTDOWN_GRACE_PERIOD=${SHUTDOWN_GRACE_PERIOD}
Environment=AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable spot-termination-handler
    systemctl start spot-termination-handler
    
    log "Systemd service created and started successfully"
}

# Function to setup node labels and taints
setup_node_labels() {
    log "Setting up node labels and taints..."
    
    # Get instance metadata
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    LOCAL_HOSTNAME=$(curl -s http://169.254.169.254/latest/meta-data/local-hostname)
    AVAILABILITY_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
    INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
    
    # Create labels file for kubelet
    cat > /etc/kubernetes/node-labels << EOF
node-lifecycle=spot
spot-instance=true
aws.amazonaws.com/ec2id=${INSTANCE_ID}
aws.amazonaws.com/availability-zone=${AVAILABILITY_ZONE}
aws.amazonaws.com/instance-type=${INSTANCE_TYPE}
app.kubernetes.io/name=market-intel-brain
app.kubernetes.io/component=${COMPONENT}
cost-optimized=true
EOF
    
    log "Node labels configured successfully"
}

# Function to configure kubelet for spot instances
configure_kubelet() {
    log "Configuring kubelet for spot instances..."
    
    # Add kubelet configuration for spot instances
    cat >> /etc/kubernetes/kubelet/config << EOF
# Spot instance configuration
nodeLabels:
  - node-lifecycle=spot
  - spot-instance=true
  - cost-optimized=true
  - app.kubernetes.io/name=market-intel-brain
  - app.kubernetes.io/component=${COMPONENT}

# Graceful termination configuration
maxPods: 110
podPidsLimit: 100
EOF
    
    # Restart kubelet to apply configuration
    systemctl restart kubelet
    
    log "Kubelet configured successfully"
}

# Function to setup monitoring for spot instances
setup_spot_monitoring() {
    log "Setting up monitoring for spot instances..."
    
    # Create CloudWatch agent configuration
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "append_dimensions": {
      "InstanceId": "\${aws:InstanceId}",
      "InstanceType": "\${aws:InstanceType}",
      "AvailabilityZone": "\${aws:AvailabilityZone}",
      "Component": "${COMPONENT}",
      "Lifecycle": "spot"
    },
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "cpu_usage_idle",
          "cpu_usage_iowait",
          "cpu_usage_user",
          "cpu_usage_system"
        ],
        "resources": [
          "*"
        ],
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          "used_percent"
        ],
        "resources": [
          "*"
        ],
        "totaldisk": false
      },
      "diskio": {
        "measurement": [
          "io_time"
        ],
        "resources": [
          "*"
        ],
        "totaldiskio": false
      },
      "mem": {
        "measurement": [
          "mem_used_percent"
        ],
        "resources": [
          "*"
      ]
      },
      "net": {
        "measurement": [
          "bytes_sent",
          "bytes_recv",
          "packets_sent",
          "packets_recv"
        ],
        "resources": [
          "*"
        ]
      }
    }
  }
}
EOF
    
    # Start CloudWatch agent
    systemctl start amazon-cloudwatch-agent
    
    log "CloudWatch agent configured successfully"
}

# Main execution
main() {
    log "Starting spot instance setup for ${COMPONENT}"
    
    # Install dependencies
    install_dependencies
    
    # Setup monitoring and logging
    setup_monitoring
    
    # Create termination handler
    create_termination_handler
    
    # Create systemd service
    create_termination_service
    
    # Setup node labels
    setup_node_labels
    
    # Configure kubelet
    configure_kubelet
    
    # Setup monitoring
    setup_spot_monitoring
    
    log "Spot instance setup completed successfully"
}

# Execute main function
main "$@"
