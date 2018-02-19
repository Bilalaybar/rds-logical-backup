# rds-logical-backup
Rds Logical Databases backup & Restore with Lambda

Usage : 
Add aws cli command in your CI process to invoke this lambda for getting backup before deployment and restore to specific version that you want.!

Example Usage:
Create some bash file and pass related parameters.

echo "================================================================================"
echo "Generating  variables...."
echo "================================================================================"
echo "DATABASE_USERNAME         : $DATABASE_USERNAME"
echo "DATABASE_PASSWORD         : ******************"
echo "DATABASE_NAME             : $DATABASE_NAME"
echo "ENVIRONMENT_NAME          : $ENVIRONMENT_NAME"
echo "DEPLOYMENT_VERSION        : $DEPLOYMENT_VERSION"
echo "MIGRATED_TO_SSM           : $MIGRATED_TO_SSM"
echo "ROLL_BACK_DB              : $ROLL_BACK_DB"
echo "AWS_REGION                : $AWS_REGION"
echo "PHASE                     : $PHASE"


cat <<EOF > $filename
{
  "database_username": "${DATABASE_USERNAME}",
  "database_password": "${DATABASE_PASSWORD}",
  "database_name": "${DATABASE_NAME}",
  "environment_name": "${ENVIRONMENT_NAME}",
  "deployment_version": "${DEPLOYMENT_VERSION}",
  "migrated_to_ssm": "${MIGRATED_TO_SSM}",
  "rollback_db": "${ROLL_BACK_DB}",
  "phase": "${PHASE}"
}
EOF

aws lambda invoke --invocation-type "RequestResponse" \
        --function-name "RDS_LOGICAL_BACKUP" \
        --region $AWS_REGION \
        --log-type "Tail" \
        --payload file://$filename \
        outfile.txt | jq -r '.LogResult' | base64 -d > outfile.txt



