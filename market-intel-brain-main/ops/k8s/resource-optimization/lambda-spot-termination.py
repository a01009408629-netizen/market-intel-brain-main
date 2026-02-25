#!/usr/bin/env python3
"""
AWS Lambda function for handling EC2 Spot Instance termination warnings
This function gracefully drains Kubernetes nodes when spot instances are terminated
"""

import boto3
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ec2_client = boto3.client('ec2')
eks_client = boto3.client('eks')

# Configuration
CLUSTER_NAME = os.environ.get('CLUSTER_NAME', 'market-intel-brain')
NAMESPACE = os.environ.get('NAMESPACE', 'market-intel-brain')
GRACE_PERIOD = int(os.environ.get('GRACE_PERIOD', '30'))
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

def setup_kubernetes():
    """Setup Kubernetes client configuration"""
    try:
        # Update kubeconfig using AWS CLI
        subprocess.run([
            'aws', 'eks', 'update-kubeconfig',
            '--name', CLUSTER_NAME,
            '--region', AWS_REGION
        ], check=True, capture_output=True)
        
        logger.info("Kubernetes configuration updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update kubeconfig: {e}")
        return False
    except Exception as e:
        logger.error(f"Error setting up Kubernetes: {e}")
        return False

def get_instance_id(event):
    """Extract instance ID from the event"""
    try:
        # Parse the event to get instance ID
        detail = event.get('detail', {})
        instance_id = detail.get('instance-id')
        
        if not instance_id:
            # Try alternative format
            instance_arn = detail.get('instance-arn', '')
            if instance_arn:
                instance_id = instance_arn.split('/')[-1]
        
        if instance_id:
            logger.info(f"Extracted instance ID: {instance_id}")
            return instance_id
        else:
            logger.error("Could not extract instance ID from event")
            return None
    except Exception as e:
        logger.error(f"Error extracting instance ID: {e}")
        return None

def get_node_name(instance_id):
    """Get Kubernetes node name from EC2 instance ID"""
    try:
        # Get node information
        result = subprocess.run([
            'kubectl', 'get', 'nodes',
            '-l', f'aws.amazonaws.com/ec2id={instance_id}',
            '-o', 'jsonpath={.items[0].metadata.name}'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            node_name = result.stdout.strip()
            logger.info(f"Found node name: {node_name}")
            return node_name
        else:
            # Try alternative method
            result = subprocess.run([
                'kubectl', 'get', 'nodes',
                '-o', 'json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                nodes = json.loads(result.stdout)
                for node in nodes.get('items', []):
                    provider_id = node.get('spec', {}).get('providerID', '')
                    if instance_id in provider_id:
                        node_name = node.get('metadata', {}).get('name')
                        logger.info(f"Found node name via provider ID: {node_name}")
                        return node_name
            
            logger.error(f"Could not find node for instance {instance_id}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout getting node name")
        return None
    except Exception as e:
        logger.error(f"Error getting node name: {e}")
        return None

def cordon_node(node_name):
    """Cordon the node to prevent new pods from being scheduled"""
    try:
        logger.info(f"Cordoning node: {node_name}")
        
        # Add termination taint
        result = subprocess.run([
            'kubectl', 'taint', 'nodes', node_name,
            'termination=spot-termination:NoSchedule',
            '--overwrite'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"Successfully added termination taint to node {node_name}")
        else:
            logger.warning(f"Failed to add termination taint: {result.stderr}")
        
        # Cordon the node
        result = subprocess.run([
            'kubectl', 'cordon', node_name
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"Successfully cordoned node {node_name}")
            return True
        else:
            logger.error(f"Failed to cordon node {node_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout cordoning node {node_name}")
        return False
    except Exception as e:
        logger.error(f"Error cordoning node {node_name}: {e}")
        return False

def drain_node(node_name):
    """Drain the node to evict pods gracefully"""
    try:
        logger.info(f"Draining node: {node_name}")
        
        # Build drain command
        cmd = [
            'kubectl', 'drain', node_name,
            '--ignore-daemonsets',
            '--delete-emptydir-data',
            '--force',
            '--grace-period', str(GRACE_PERIOD),
            '--timeout', str(GRACE_PERIOD + 10) + 's'
        ]
        
        # Execute drain command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=GRACE_PERIOD + 15)
        
        if result.returncode == 0:
            logger.info(f"Successfully drained node {node_name}")
            return True
        else:
            logger.error(f"Failed to drain node {node_name}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout draining node {node_name}")
        return False
    except Exception as e:
        logger.error(f"Error draining node {node_name}: {e}")
        return False

def get_pod_info(node_name):
    """Get information about pods running on the node"""
    try:
        logger.info(f"Getting pod information for node: {node_name}")
        
        result = subprocess.run([
            'kubectl', 'get', 'pods',
            '--field-selector', f'spec.nodeName={node_name}',
            '-n', NAMESPACE,
            '-o', 'json'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            pods = json.loads(result.stdout)
            pod_count = len(pods.get('items', []))
            
            # Get pod details
            pod_details = []
            for pod in pods.get('items', []):
                pod_name = pod.get('metadata', {}).get('name', 'unknown')
                pod_namespace = pod.get('metadata', {}).get('namespace', 'unknown')
                pod_phase = pod.get('status', {}).get('phase', 'unknown')
                
                pod_details.append({
                    'name': pod_name,
                    'namespace': pod_namespace,
                    'phase': pod_phase
                })
            
            logger.info(f"Found {pod_count} pods on node {node_name}")
            return pod_details
        else:
            logger.error(f"Failed to get pod information: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout getting pod information")
        return []
    except Exception as e:
        logger.error(f"Error getting pod information: {e}")
        return []

def send_notification(node_name, instance_id, pod_info):
    """Send notification about node termination"""
    try:
        # Create notification message
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'cluster': CLUSTER_NAME,
            'namespace': NAMESPACE,
            'node': node_name,
            'instance_id': instance_id,
            'event': 'spot-instance-termination',
            'pod_count': len(pod_info),
            'pods': pod_info,
            'grace_period': GRACE_PERIOD
        }
        
        # Log notification
        logger.info(f"Spot termination notification: {json.dumps(message, indent=2)}")
        
        # Here you could add SNS notification, Slack notification, etc.
        # For now, just log the information
        
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

def handler(event, context):
    """Main Lambda handler function"""
    logger.info(f"Received event: {json.dumps(event, indent=2)}")
    
    # Setup Kubernetes
    if not setup_kubernetes():
        logger.error("Failed to setup Kubernetes, exiting")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to setup Kubernetes'})
        }
    
    # Extract instance ID
    instance_id = get_instance_id(event)
    if not instance_id:
        logger.error("Could not extract instance ID from event")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Could not extract instance ID'})
        }
    
    # Get node name
    node_name = get_node_name(instance_id)
    if not node_name:
        logger.error(f"Could not find node for instance {instance_id}")
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Could not find node'})
        }
    
    # Get pod information
    pod_info = get_pod_info(node_name)
    
    # Send notification
    send_notification(node_name, instance_id, pod_info)
    
    # Cordon the node
    if not cordon_node(node_name):
        logger.error(f"Failed to cordon node {node_name}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to cordon node'})
        }
    
    # Wait a bit before draining
    time.sleep(5)
    
    # Drain the node
    if not drain_node(node_name):
        logger.error(f"Failed to drain node {node_name}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to drain node'})
        }
    
    # Success
    logger.info(f"Successfully handled spot termination for node {node_name}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Spot termination handled successfully',
            'node': node_name,
            'instance_id': instance_id,
            'pod_count': len(pod_info)
        })
    }

# Test function for local testing
def test_handler():
    """Test function for local testing"""
    test_event = {
        'version': '0',
        'id': 'test-id',
        'detail-type': 'EC2 Spot Instance Interruption Warning',
        'source': 'aws.ec2',
        'account': '123456789012',
        'time': '2023-01-01T00:00:00Z',
        'region': 'us-east-1',
        'resources': ['arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0'],
        'detail': {
            'instance-id': 'i-1234567890abcdef0',
            'instance-action': 'terminate'
        }
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
            self.memory_limit_in_mb = 128
            self.aws_request_id = 'test-request-id'
            self.log_group_name = '/aws/lambda/test-function'
            self.log_stream_name = '2023/01/01/[$LATEST]test-stream'
            self.get_remaining_time_in_millis = lambda: 30000
    
    return handler(test_event, MockContext())

if __name__ == '__main__':
    # For local testing
    print("Testing spot termination handler...")
    result = test_handler()
    print(f"Result: {result}")
