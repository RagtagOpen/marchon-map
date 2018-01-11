# Monitoring setup

1. Ensure target service has cloudwatch log update permissions. verify log output!
2. Update or create lambda execution role, requires
    * lambda execution
    * cloudwatch log access
    * SNS publish  
3. Update or create SNS topic
4. Add subscription(s) to topic (with filters if desired, attributes TBD)
5. Create monitoring lambda function
    * zipped deployment package
    * Environment variables
    * execution role
6. Ensure monitoring lambda has read permissions on service logs and publish perms on SNS topic
7. Create cloudwatch log metric on target service log group, bound to monitoring lambda 