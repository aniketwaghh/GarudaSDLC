# AWS Infrastructure Setup Scripts

This folder contains AWS infrastructure setup scripts for the Garuda SDLC platform.

## Scripts

### `setup-eventbridge-role.sh`

Creates and configures the IAM role required for EventBridge Scheduler to invoke API destinations.

**What it does:**
- Creates `EventBridgeSchedulerRole` IAM role (if it doesn't exist)
- Sets up trust relationships for `scheduler.amazonaws.com` and `events.amazonaws.com`
- Attaches permissions to:
  - Put events to the default EventBridge event bus
  - Invoke API destinations matching the pattern `g-hook-*`

**Usage:**
```bash
./aws/setup-eventbridge-role.sh
```

**Requirements:**
- AWS CLI installed and configured
- Sufficient IAM permissions to create/update roles and policies
- Account ID and region are hardcoded in the script (update if needed)

**Role Details:**
- **Role Name:** `EventBridgeSchedulerRole`
- **Role ARN:** `arn:aws:iam::679835924842:role/EventBridgeSchedulerRole`
- **Trust Policy:** Allows EventBridge Scheduler and Events services
- **Permissions:** PutEvents and InvokeApiDestination

**Configuration:**
The role ARN is configured in:
- `services/requirement_gathering/.env` as `AWS_EVENTBRIDGE_ROLE_ARN`

## Architecture

EventBridge Scheduler uses the following flow:
```
Scheduler → Event Bus → Event Rule → API Destination → HTTP Endpoint
```

The IAM role is used by:
1. **Scheduler** to put events on the event bus
2. **Event Bus** to invoke the API destination when rules match

## Troubleshooting

If you see errors about role trust policies:
1. Run `./aws/setup-eventbridge-role.sh` to recreate/update the role
2. Verify the role ARN in your `.env` file matches the output
3. Restart the requirement_gathering service to pick up changes
