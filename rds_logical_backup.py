from __future__ import print_function
import boto3
import commands
import os
import socket
from shutil import copyfile
import botocore

printer = lambda x : print(x)
credentials= []
database_username=""
database_password=""
database_name=""
environment_name=""
deployment_version=""
migrated_to_ssm=""
rollback_db=""
phase=""
current_account_id=""
database_endpoint=""
def lambda_handler(event, context):
    # set variables from EVENT
    global database_username
    global database_password
    global database_name
    global environment_name
    global deployment_version
    global migrated_to_ssm
    global rollback_db
    global phase

    database_username = event['database_username']
    database_password = event['database_password']
    database_name = event['database_name']
    environment_name = event['environment_name']
    deployment_version = event['deployment_version']
    migrated_to_ssm = event['migrated_to_ssm']
    rollback_db = event['rollback_db']
    phase = event['phase']

    do_basics(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm)
    database_name = database_name.lower()
    if phase in "deploy":
        take_dump(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm)
    elif (phase == "rollback") and (rollback_db == "1"):
        db_rollbacker(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm)

def take_dump(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm):
    os.environ['PATH']
    copyfile("/var/task/pg_dump","/tmp/pg_dump")
    os.chmod("/tmp/",0o777)
    os.putenv('PGPASSWORD', database_password)

    file = open('/tmp/output.txt', 'w+')
    os.chmod("/tmp/pg_dump", 0o755)

    os.system('rm -rf /tmp/output.txt')
    pg_dump_command = "PGPASSWORD=" + database_password + " /tmp/pg_dump -h " + database_endpoint + " -p 5432 -U "+ database_username + " " + database_name +" --format=c"+" > /tmp/output.txt"

    #Open it for debug purposes
    #printer("my command is " + pg_dump_command)

    printer(commands.getoutput(pg_dump_command))

    #To see whether dump file is created
    content_list = []
    for content in os.listdir("/tmp/"): # "." means current directory
        content_list.append(content)
    printer(content_list)

    s3 = boto3.resource('s3')
    BUCKET = "logical-backup-bucket-"+current_account_id
    key = database_name+'/'+environment_name+'/'+database_name+'-'+environment_name+'-'+deployment_version+'.sql'
    try:
        s3.Bucket(BUCKET).upload_file("/tmp/output.txt", key)
    except Exception as e: #code to run if error occurs
        printer(e)
        printer(" Backup operation is not successful!")
    else:
        printer("Backup operation is successful!")

def db_rollbacker(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm):

    os.environ['PATH']

    client = boto3.client('rds')

    copyfile("/var/task/pg_restore","/tmp/pg_restore")
    copyfile("/var/task/psql.bin","/tmp/psql.bin")
    copyfile("/var/task/libedit.so.0","/tmp/libedit.so.0")
    copyfile("/var/task/libncurses.so.6","/tmp/libncurses.so.6")
    os.chmod("/tmp/",0o777)
    os.putenv('PGPASSWORD', database_password)

    file = open('/tmp/output.txt', 'w+')
    os.chmod("/tmp/pg_restore", 0o755)
    os.chmod("/tmp/psql.bin", 0o755)
    os.chmod("/tmp/libedit.so.0", 0o755)
    os.chmod("/tmp/libncurses.so.6", 0o755)
    os.system('rm -rf /tmp/output.txt')
    BUCKET_NAME = "logical-backup-bucket-"+current_account_id
    KEY = database_name+'/'+environment_name+'/'+database_name+'-'+environment_name+'-'+deployment_version+'.sql'

    s3 = boto3.resource('s3')

    try:
        s3.Bucket(BUCKET_NAME).download_file(KEY, '/tmp/rollback.dump')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    pg_restore_command = "PGPASSWORD=" + database_password + " /tmp/pg_restore  --clean --exit-on-error --verbose -n public -h " + database_endpoint + " -p 5432 -U "+ database_username + " --dbname=" + database_name + " /tmp/rollback.dump"
    #Open it for debug purposes
    #printer("my command is " + pg_restore_command)

    printer(commands.getoutput(pg_restore_command))

    #To see whether dump file is created
    content_list = []
    for content in os.listdir("/tmp/"): # "." means current directory
        content_list.append(content)
    printer(content_list)

def do_basics(database_username,database_password,database_name,environment_name,deployment_version,migrated_to_ssm):
    """Some of the projects username and passwords are not migrated to ssm still in gitlab's environment variable
    and some of them are exist in ssm"""
    get_db_credentials()
    #Fetch Database endpoint according to the service and environment name
    get_db_endpoint()
    #get account Id for determining bucket that our dump will be saved
    get_account_id()
    #check lambda can reach database endpoint
    check_connection_for_db()

def get_db_credentials():
    global database_username
    global database_password
    if migrated_to_ssm == "true":
        ssm_client = boto3.client('ssm')
        ssm_parameters = ssm_client.get_parameters(
            Names=[database_username,database_password],
            WithDecryption=True
        )
        database_username = ssm_parameters['Parameters'][0]['Value']
        database_password = ssm_parameters['Parameters'][1]['Value']

def get_db_endpoint():
    global database_name
    global database_endpoint
    if "preview" in environment_name:
        database_name = "preview"
    #if you want to use this lambda on EDGE-PREVIEW you have to uncomment above lines
    rds_client = boto3.client('rds')
    all_rds_instances = rds_client.describe_db_instances()
    db_instances = all_rds_instances.get('DBInstances')

    for i in range(0,len(db_instances)):
        if database_name in db_instances[i]['Endpoint']['Address']:
            database_endpoint = db_instances[i]['Endpoint']['Address']
            printer("Endpoint is  : " + db_instances[i]['Endpoint']['Address'])
            printer("Database name is : " +database_name)
            if environment_name == "team-ist-06" and environment_name in database_endpoint:
                break
            if environment_name == "team-ist-07" and environment_name in database_endpoint:
                break
            if environment_name == "team-ist-08" and environment_name in database_endpoint:
                break
    printer("Database dump operation will be on : "+database_endpoint)

def get_account_id():
    global current_account_id
    current_account_id = boto3.client('sts').get_caller_identity()['Account']
    printer( "current account id is : " + current_account_id)

def check_connection_for_db():
    #check lambda can reach database endpoint
    global database_endpoint
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((database_endpoint,5432))

    if result == 0:
        printer("It's OK!Lambda can reach db endpoint!")
    else:
        printer("Oppss..Lambda cannot reach to the database endpoint!")

