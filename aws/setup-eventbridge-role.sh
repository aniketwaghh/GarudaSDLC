#!/bin/bash

# Setup EventBridge Scheduler IAM Role
# This script configures the IAM role with proper trust relationships and permissions
# for EventBridge Scheduler and Events to work with API Destinations

set -e

ROLE_NAME="EventBridgeSchedulerRole"
ACCOUNT_ID="679835924842"
REGION="us-west-2"

echo "🔧 Setting up IAM role: $ROLE_NAME"
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Check if role exists
if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
    echo "✓ Role already exists"
else
    echo "Creating role..."
    ROLE_CREATED=true
fi
echo ""

# Create trust policy JSON
cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "scheduler.amazonaws.com",
          "events.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create permissions policy JSON
cat > /tmp/eventbridge-permissions.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "events:PutEvents"
      ],
      "Resource": "arn:aws:events:*:*:event-bus/default"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:InvokeApiDestination"
      ],
      "Resource": "arn:aws:events:*:*:api-destination/g-hook-*"
    }
  ]
}
EOF

echo "📝 Updating trust policy for role: $ROLE_NAME"

# Create role if it doesn't exist
if [ "${ROLE_CREATED}" = "true" ]; then
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for EventBridge Scheduler to invoke API destinations"
    echo "✅ Role created"
else
    # Update existing role's trust policy
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/trust-policy.json
    echo "✅ Trust policy updated"
fi

echo "✅ Trust policy updated"
echo ""

# Create or update inline policy
POLICY_NAME="EventBridgeSchedulerPermissions"

echo "📝 Putting inline policy: $POLICY_NAME"
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document file:///tmp/eventbridge-permissions.json

echo "✅ Permissions policy attached"
echo ""

# Display current role configuration
echo "📋 Current role configuration:"
echo ""
echo "Trust Policy:"
aws iam get-role --role-name "$ROLE_NAME" --query 'Role.AssumeRolePolicyDocument' --output json
echo ""

echo "Inline Policies:"
aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" --query 'PolicyDocument' --output json
echo ""

# Cleanup temp files
rm -f /tmp/trust-policy.json /tmp/eventbridge-permissions.json

echo "✅ Setup complete!"
echo ""
echo "Role ARN: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
echo ""
echo "You can now create EventBridge schedules with this role."
