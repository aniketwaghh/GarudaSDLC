"""
AWS EventBridge Scheduler utilities for meeting scheduling.
"""

import os
import json
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class EventBridgeScheduler:
    """
    Manages AWS EventBridge Scheduler for scheduling meeting bot joins.
    """
    
    def __init__(
        self,
        aws_region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        role_arn: Optional[str] = None,
    ):
        """
        Initialize EventBridge Scheduler client.
        
        Args:
            aws_region: AWS region (default from env)
            aws_access_key_id: AWS access key (default from env)
            aws_secret_access_key: AWS secret key (default from env)
            role_arn: IAM role ARN for EventBridge (default from env)
        """
        self.region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.role_arn = role_arn or os.getenv("AWS_EVENTBRIDGE_ROLE_ARN")
        
        # Initialize boto3 clients
        credentials = {
            "region_name": self.region,
            "aws_access_key_id": aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
        }
        
        self.scheduler_client = boto3.client("scheduler", **credentials)
        self.events_client = boto3.client("events", **credentials)
        
        # Get default event bus ARN
        self.event_bus_name = "default"
        account_id = boto3.client("sts", **credentials).get_caller_identity()["Account"]
        self.event_bus_arn = f"arn:aws:events:{self.region}:{account_id}:event-bus/{self.event_bus_name}"
    
    def _get_or_create_api_destination(
        self,
        name: str,
        webhook_url: str,
    ) -> str:
        """
        Get or create an EventBridge API Destination for the webhook.
        
        Args:
            name: Destination name
            webhook_url: Target URL
            
        Returns:
            API Destination ARN
        """
        destination_name = f"g-hook-{name}"
        connection_name = f"g-conn-{name}"
        
        try:
            # Try to get existing destination
            response = self.events_client.describe_api_destination(Name=destination_name)
            return response['ApiDestinationArn']
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        try:
            # Create connection first (required for API destination)
            conn_response = self.events_client.create_connection(
                Name=connection_name,
                AuthorizationType='API_KEY',
                AuthParameters={
                    'ApiKeyAuthParameters': {
                        'ApiKeyName': 'X-Api-Key',
                        'ApiKeyValue': 'garuda-internal-key'
                    }
                }
            )
            connection_arn = conn_response['ConnectionArn']
            
            # Create API destination
            dest_response = self.events_client.create_api_destination(
                Name=destination_name,
                ConnectionArn=connection_arn,
                InvocationEndpoint=webhook_url,
                HttpMethod='POST',
                InvocationRateLimitPerSecond=10
            )
            return dest_response['ApiDestinationArn']
            
        except ClientError as e:
            print(f"❌ Failed to create API destination: {e.response['Error']}")
            raise Exception(f"Failed to create API destination: {e.response['Error']['Message']}")
    
    def _get_or_create_event_rule(
        self,
        name: str,
        api_destination_arn: str,
        description: str = "",
    ) -> str:
        """
        Get or create an EventBridge rule that routes to the API destination.
        
        Args:
            name: Rule name
            api_destination_arn: Target API destination ARN
            description: Rule description
            
        Returns:
            Rule ARN
        """
        rule_name = f"g-rule-{name}"
        
        try:
            # Try to get existing rule
            response = self.events_client.describe_rule(
                Name=rule_name,
                EventBusName=self.event_bus_name
            )
            return response['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        try:
            # Create the rule with a pattern matching our schedule events
            rule_response = self.events_client.put_rule(
                Name=rule_name,
                EventBusName=self.event_bus_name,
                Description=description or f"Route schedule {name} to API destination",
                State='ENABLED',
                EventPattern=json.dumps({
                    "source": ["garuda.scheduler"],
                    "detail-type": [f"Scheduled Event {name}"]
                })
            )
            rule_arn = rule_response['RuleArn']
            
            # Add the API destination as a target for this rule
            self.events_client.put_targets(
                Rule=rule_name,
                EventBusName=self.event_bus_name,
                Targets=[{
                    'Id': '1',
                    'Arn': api_destination_arn,
                    'RoleArn': self.role_arn,
                    'HttpParameters': {
                        'HeaderParameters': {
                            'Content-Type': 'application/json'
                        }
                    },
                    'RetryPolicy': {
                        'MaximumRetryAttempts': 3,
                        'MaximumEventAgeInSeconds': 3600
                    },
                    'InputPath': '$.detail.payload'
                }]
            )
            
            return rule_arn
            
        except ClientError as e:
            print(f"❌ Failed to create rule: {e.response['Error']}")
            raise Exception(f"Failed to create event rule: {e.response['Error']['Message']}")
    
    def create_schedule(
        self,
        name: str,
        cron_expression: str,
        webhook_url: str,
        payload: Dict[str, Any],
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create a schedule that triggers an HTTP POST webhook via API Destination.
        
        Args:
            name: Unique schedule name
            cron_expression: Cron expression (e.g., "cron(0 10 * * ? *)" for 10 AM daily)
            webhook_url: URL to call when schedule triggers
            payload: JSON payload to send in POST request
            description: Optional description
            
        Returns:
            Schedule ARN and details
            
        Raises:
            ClientError: If schedule creation fails
        """
        try:
            # Get or create API destination for this webhook
            api_destination_arn = self._get_or_create_api_destination(name, webhook_url)
            
            # Get or create event rule that routes to the API destination
            rule_arn = self._get_or_create_event_rule(name, api_destination_arn, description)
            
            # Create event detail with the payload nested
            event_detail = {
                "payload": payload,
                "schedule_name": name
            }
            
            response = self.scheduler_client.create_schedule(
                Name=name,
                Description=description,
                ScheduleExpression=cron_expression,
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={
                    "Arn": self.event_bus_arn,
                    "RoleArn": self.role_arn,
                    "EventBridgeParameters": {
                        "DetailType": f"Scheduled Event {name}",
                        "Source": "garuda.scheduler"
                    },
                    "Input": json.dumps(event_detail),
                    "RetryPolicy": {
                        "MaximumRetryAttempts": 3,
                        "MaximumEventAgeInSeconds": 3600
                    }
                },
                State="ENABLED",
                ActionAfterCompletion="DELETE"  # Auto-delete schedule after it fires
            )
            
            return {
                "schedule_arn": response["ScheduleArn"],
                "name": name,
                "status": "created"
            }
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            print(f"❌ EventBridge error: {e.response['Error']}")
            
            # Provide helpful guidance for common errors
            if "assume the role" in error_msg.lower():
                raise Exception(
                    f"Failed to create schedule: IAM role trust policy issue. "
                    f"The role {self.role_arn} must have a trust relationship allowing "
                    f"'scheduler.amazonaws.com' and 'events.amazonaws.com' to assume it. "
                    f"Add this to the role's trust policy: "
                    f'{{"Version": "2012-10-17", "Statement": [{{"Effect": "Allow", '
                    f'"Principal": {{"Service": ["scheduler.amazonaws.com", "events.amazonaws.com"]}}, '
                    f'"Action": "sts:AssumeRole"}}]}}'
                )
            
            raise Exception(f"Failed to create schedule: {error_msg}")
    
    def delete_schedule(self, name: str) -> bool:
        """
        Delete a schedule by name and cleanup associated resources.
        
        Args:
            name: Schedule name
            
        Returns:
            True if deleted successfully
            
        Raises:
            ClientError: If deletion fails
        """
        try:
            # Delete the schedule
            self.scheduler_client.delete_schedule(Name=name)
            
            # Try to cleanup event rule
            rule_name = f"g-rule-{name}"
            try:
                # Remove targets first
                self.events_client.remove_targets(
                    Rule=rule_name,
                    EventBusName=self.event_bus_name,
                    Ids=['1']
                )
                # Then delete the rule
                self.events_client.delete_rule(
                    Name=rule_name,
                    EventBusName=self.event_bus_name
                )
            except ClientError:
                pass  # May not exist
            
            # Try to cleanup API destination and connection
            destination_name = f"g-hook-{name}"
            connection_name = f"g-conn-{name}"
            
            try:
                self.events_client.delete_api_destination(Name=destination_name)
            except ClientError:
                pass  # May not exist
            
            try:
                self.events_client.delete_connection(Name=connection_name)
            except ClientError:
                pass  # May not exist
            
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise Exception(f"Failed to delete schedule: {e.response['Error']['Message']}")
    
    def get_schedule(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get schedule details.
        
        Args:
            name: Schedule name
            
        Returns:
            Schedule details or None if not found
        """
        try:
            response = self.scheduler_client.get_schedule(Name=name)
            return {
                "name": response["Name"],
                "arn": response["Arn"],
                "state": response["State"],
                "schedule_expression": response["ScheduleExpression"],
                "target": response["Target"],
                "description": response.get("Description", "")
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise Exception(f"Failed to get schedule: {e.response['Error']['Message']}")
    
    def update_schedule(
        self,
        name: str,
        cron_expression: Optional[str] = None,
        webhook_url: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        state: Optional[str] = None,
    ) -> bool:
        """
        Update an existing schedule.
        
        Args:
            name: Schedule name
            cron_expression: New cron expression (optional)
            webhook_url: New webhook URL (optional)
            payload: New payload (optional)
            state: New state "ENABLED" or "DISABLED" (optional)
            
        Returns:
            True if updated successfully
        """
        try:
            # Get current schedule
            current = self.scheduler_client.get_schedule(Name=name)
            
            # Prepare update parameters
            update_params = {
                "Name": name,
                "ScheduleExpression": cron_expression or current["ScheduleExpression"],
                "FlexibleTimeWindow": current["FlexibleTimeWindow"],
                "Target": current["Target"],
            }
            
            if state:
                update_params["State"] = state
            else:
                update_params["State"] = current.get("State", "ENABLED")
            
            # Update target if webhook or payload changed
            if webhook_url or payload:
                current_input = json.loads(current["Target"]["Input"])
                
                if webhook_url:
                    current_input["Url"] = webhook_url
                
                if payload:
                    current_input["Body"] = json.dumps(payload)
                
                update_params["Target"]["Input"] = json.dumps(current_input)
            
            self.scheduler_client.update_schedule(**update_params)
            return True
            
        except ClientError as e:
            raise Exception(f"Failed to update schedule: {e.response['Error']['Message']}")
    
    def get_schedule(self, name: str) -> Dict[str, Any]:
        """
        Get details of a schedule including its execution status.
        
        Args:
            name: Schedule name
            
        Returns:
            Schedule details including ARN, state, cron expression, and next execution time
        """
        try:
            response = self.scheduler_client.get_schedule(Name=name)
            return {
                "name": response["Name"],
                "arn": response["Arn"],
                "state": response["State"],
                "cron_expression": response["ScheduleExpression"],
                "description": response.get("Description", ""),
                "created_at": response.get("CreationDate"),
                "last_modified": response.get("LastModificationDate"),
                "action_after_completion": response.get("ActionAfterCompletion", "NONE"),
                "target": response.get("Target", {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise Exception(f"Failed to get schedule: {e.response['Error']['Message']}")


def get_scheduler() -> EventBridgeScheduler:
    """
    Factory function to create scheduler instance from environment variables.
    
    Returns:
        Configured EventBridgeScheduler instance
    """
    return EventBridgeScheduler(
        aws_region=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        role_arn=os.getenv("AWS_EVENTBRIDGE_ROLE_ARN"),
    )
