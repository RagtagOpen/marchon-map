# Monitoring design

The ragtag monitoring solution involves the following AWS objects:

* **application** - the lambda resource to monitor. 
* **application service role** - the service role assigned to the application resource
* **application log** - the CloudWatch Logs group associated with the application resource.
* **monitor** - the monitoring resource. in the current design, every application requires a dedicated monitor instance. We're looking into ways to
   parameterize the monitor to allow the same monitor to support multiple applications.
* **monitor service role** - the security role assigned to the monitor resource.
* **monitor log** - the CloudWatch Logs group associated with the monitoring resource
* **monitoring subscription** - a CloudWatch Log subscription that invokes the monitor when it detects an application request has completed.
* **reporting topic** - an SNS topic used to deliver monitor reports to interested subscribers
* **reporting subscription** - a subscription on the reporting topic that delivers monitoring-related messages to end users or other channels.

1. Verify/Update marchon lambda permissions
2. Create/Update marchon log group
3. Create/Update SNS topic and subscription(s) for status reports
4. Create/update security role / permissions for monitoring component 
5. Create new lambda function for log analysis and reporting
6. Create new log subscription to watch marchon logs for request completion

# Packaging

Create monitoring lambda function
    * zipped deployment package
    * Environment variables
    * execution role

# Setup

## Configure application role

The application lambda function must have permissions to update CloudWatch Logs. Ensure the application service role (e.g. `marchon-lambda-role`) includes the following minimum permissions :

	{
	    "Version": "2012-10-17",
	    "Statement": [
	        {
	            "Action": [
	                "logs:CreateLogGroup",
	                "logs:CreateLogStream",
	                "logs:PutLogEvents"
	            ],
	            "Effect": "Allow",
	            "Resource": "*"
	        }
	    ]
	}

## Create application log group

If the application has already run (and had `CreateLogGroup` permissions), the CloudWatch logs group may already exist. Otherwise create it directly, as
`/aws/lambda/`*function-name*

	aws logs create-log-group --log-group-name /aws/lambda/<function-name>
	# set retention policy (optional, defaults to None)
	aws logs put-retention-policy --log-group-name /aws/lambda/<function-name> --retention-in-days 30

## Configure application logging

AWS Lambda will automatically log events when a request starts and ends. To add additional information about progress, warnings, and errors:

Do not change the default logging pattern. The monitoring service looks for specific fields in the log events.


## Create the reporting topic

	TOPIC_ARN=`aws sns create-topic --name app-monitoring-reports --output text`
	aws sns set-topic-attributes \
	        --topic-arn $TOPIC_ARN \
	        --attribute-name DisplayName \
	        --attribute-value "Topic for log monitoring"

## Create the topic subscription

    aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint <email-address>
    
Someone with access to the endpoint email address will have to confirm the subscription
(by clicking on a link in the confirmation request). The confirmation request will include the ARN of the
subscription.

	SUB_ARN=<subscription-arn>
    
## Add a subscription delivery policy

A delivery policy allows a subscriber to limit the messages forwarded to the endpoint.

	aws sns set-subscription-attributes -out text \
	        --subscription-arn $SUB_ARN  \
	        --attribute-name DeliveryPolicy \
	        --attribute-value <filter-policy>
                                        
The *filter-policy* is a map of message attributes to possible values. For example, the
following policy would only deliver reports for requests for a specific lambda function that had more than one error or warning:

	{
	  "name": "hello-world"
	  "status": ["error","warning"]
	}

Monitoring report messages support the following attributes:

* `function` the lambda function name, e.g. `hello-world`.
* `name`     the application display name, e.g. "Hello world!"
* `status`    function execution status, one of `error`, `warning`, or `success`.
* `warnings`  the number of warnings reported
* `errors`    the number of errors reported

See [Filtering Messages with Amazon SNS](https://docs.aws.amazon.com/sns/latest/dg/message-filtering.html]) 
for more information about filter policies.


## Configure monitor service role

Define a security policy with read/write access to logs and publishing permissions on SNS topics:

	{
	  "Version": "2012-10-17",
	  "Statement": [
	    {
	      "Sid": "PublishReporting"
	      "Effect": "Allow",
	      "Action": ["sns:Publish"],
	      "Resource": [ 
	         "arn:aws:sns::187976421381:app-monitoring-reports",
	       ],
	    },    
	    {
	      "Sid": "ReadLogs"
	      "Effect": "Allow",
	      "Action": [
	                 "logs:GetLogEvents", 
	                 "logs:FilterLogEvents",
	                 ],
	      "Resource": [ 
	        "arn:aws:logs::187976421381:log-group:/aws/lambda/monitor-lambda-logs:*", 
	      ],
	    }
	  ]
	}
	
Create the policy

	aws iam create-policy \
	  --policy-name monitoring-lambda \
	  --description "Security policy for monitoring lambdas. Provides permissions to access CloudWatch logs and publish to SNS topics." \
	  --policy-document file://monitor-lambda-policy.json

Create or update a security role 
    
	aws iam create-role \
	   --role-name monitoring-lambda \
	   --description "Security role for monitoring lambda function executions. Provides permissions to access logs and publish to a topic." \
	   --assume-role-policy-document file://lambda-assume-role-policy.json
	ROLE_ARN=`aws iam list-roles --output text --query "Roles[?RoleName=='monitoring-lambda'].[Arn]"`

Add base and monitoring policies to security role

	LAMBDA_POLICY_ARN=`aws iam list-policies --output text --query "Policies[?PolicyName=='marchon-lambda-role'].[Arn]"`
	aws iam attach-role-policy \
			--role-name "monitoring-lambda" \
			--policy-arn "$LAMBDA_POLICY_ARN"
	MONITOR_POLICY_ARN=`aws iam list-policies --output text --query "Policies[?PolicyName=='monitoring-lambda'].[Arn]"`
	aws iam attach-role-policy \
			--role-name "monitoring-lambda" \
			--policy-arn "$MONITOR_POLICY_ARN"

## Create monitoring lambda function

Create a new lambda function

	aws lambda create-function \
	    --function-name monitor_lambda \
	    --runtime python3.6 \
	    --role "$ROLE_ARN" \
	    --handler monitor_lambda_runs.lambda_handler \
	    --description 'Monitor log output from lambda execution requests' 
	    

role: the monitor security role set up in the previous step

code: upload zip file (or s3?)

required environment variables:
* **APPLICATION_NAME** - the friendly name of the application, used in reporting
* **APPLICATION_LOG_GROUP_NAME** - the application log group, e.g. `/aws/lambda/hello-world`
* **REPORTING_TOPIC_ARN** - the ARN of the reporting topic

optional environment variables:
* **LOG_LEVEL** - log level for the monitoring application, defaults to `INFO`
* **DRY_RUN** - if `True`, dumps report messages to the monitoring log instead of publishing to the reporting topic. Default is `False`. Useful for verifying monitoring configuration prior to going live

## Configure the monitoring subscription

Create a new CloudWatch Logs subscription, as

log group: **SERVICE_LOG_GROUP**
filter pattern: <TBD>
action: lambda, monitoring resource ARN

# Notes

Consider defining a separate test monitor (with DRY_RUN true) and monitoring subscription for validation prior to updating production monitor lambda.
