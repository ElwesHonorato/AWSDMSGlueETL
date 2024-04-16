
import boto3
import os
import pymysql
import botocore
from botocore.exceptions import ClientError
import json


def connect_to_mysql(
        host, 
        user, 
        password, 
        database, 
        connect_timeout=5
    ) -> pymysql.connections.Connection:
    """
    Establishes a connection to a MySQL database.

    Args:
        host (str): The hostname or IP address of the MySQL server.
        user (str): The username for authenticating with the MySQL server.
        password (str): The password for authenticating with the MySQL server.
        database (str): The name of the MySQL database to connect to.
        connect_timeout (int, optional): The timeout for establishing the connection, in seconds. Default is 5.

    Returns:
        pymysql.connections.Connection: A connection object representing the connection to the MySQL database.
    """
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connect_timeout=connect_timeout
        )
        print("Connected to MySQL")
        return connection
    except Exception as e:
        print("Error:", e)
        raise e


def connect_to_s3() -> botocore.client.BaseClient:
    """
    Establishes a connection to AWS S3.

    Returns:
        boto3.client.S3: A client object for interacting with AWS S3.
    """
    try:
        connection = boto3.client('s3')
        print("Connected to S3")
        return connection
    except Exception as e:
        print("Error:", e)
        raise e


def connect_to_codecommit() -> botocore.client.BaseClient:
    """
    Establishes a connection to AWS CodeCommit.

    Returns:
        boto3.client.CodeCommit: A client object for interacting with AWS CodeCommit.
    """
    try:
        connection = boto3.client('codecommit')
        print("Connected to CodeCommit")
        return connection
    except Exception as e:
        print("Error:", e)
        raise e


def get_secret(
        secret_name: str, 
        region_name: str = "us-east-1"
    ) -> tuple:
    """
    Retrieves secret credentials from AWS Secrets Manager.

    Args:
        secret_name (str): The name or ARN of the secret to retrieve.
        region_name (str, optional): The AWS region where the secret is located. Default is "us-east-1".

    Returns:
        tuple: A tuple containing the username and password retrieved from Secrets Manager.
        
    Raises:
        ClientError: If an error occurs while retrieving the secret.

    Note:
        If the secret contains a 'SecretString', it is assumed to be a JSON object containing 'username' and 'password' keys.
        If the secret contains a 'SecretBinary', it is assumed to be base64 encoded and decoded to obtain the binary secret.
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        print(get_secret_value_response)
    except ClientError as e:
        print("Error:", e)
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            secret_dict = json.loads(secret)
            rds_username = secret_dict['username']
            rds_password = secret_dict['password']
            return rds_username, rds_password
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret


def list_files_code_commit(
        conn_codecommit : botocore.client.BaseClient, 
        repository_name : str, 
        branch_name : str, 
        folder_path : str
    ) -> list:
    """
    Lists files in a specified folder of a CodeCommit repository.

    Args:
        conn_codecommit (botocore.client.BaseClient): A client object for interacting with AWS CodeCommit.
        repository_name (str): The name of the CodeCommit repository.
        branch_name (str): The name of the branch in the repository.
        folder_path (str): The path to the folder in the repository.

    Returns:
        list: A list of absolute file paths in the specified folder.
    """
    response = conn_codecommit.get_branch(
        repositoryName=repository_name,
        branchName=branch_name
    )
    commit_id = response['branch']['commitId']
    
    response = conn_codecommit.get_folder(
        repositoryName=repository_name,
        folderPath=folder_path,
        commitSpecifier=commit_id
    )
    files = response['files']
    files_path = []
    for file in files:
        file_path = file['absolutePath']
        files_path.append(file_path)
    return files_path


def get_file_content(
        conn_codecommit : botocore.client.BaseClient, 
        repository_name : str, 
        branch_name : str, 
        absolute_file_path : str
    ) -> str:
    """
    Retrieves the content of a file from AWS CodeCommit.

    Args:
        conn_codecommit (botocore.client.BaseClient): A client object for interacting with AWS CodeCommit.
        repository_name (str): The name of the CodeCommit repository.
        branch_name (str): The name of the branch in the repository.
        absolute_file_path (str): The absolute path to the file in the repository.

    Returns:
        str: The content of the file.
    """
    response = conn_codecommit.get_file(
        repositoryName=repository_name,
        commitSpecifier=branch_name,
        filePath=absolute_file_path
    )
    file_content = response['fileContent'].decode('utf-8')
    return file_content


def get_code_commit_files_content(
        conn_codecommit : botocore.client.BaseClient, 
        repository_name : str, 
        branch_name : str, 
        files_path : str
        ) -> dict:
    """
    Retrieves the content of multiple files from AWS CodeCommit.

    Args:
        conn_codecommit (botocore.client.BaseClient): A client object for interacting with AWS CodeCommit.
        repository_name (str): The name of the CodeCommit repository.
        branch_name (str): The name of the branch in the repository.
        files_path (list): A list of absolute file paths in the repository.

    Returns:
        dict: A dictionary containing file paths as keys and file contents as values.
    """
    content_dict = {}
    for file_path in files_path:
        file_content = get_file_content(
            conn_codecommit,
            repository_name,
            branch_name,
            file_path
        )
        content_dict[file_path] = file_content
    return content_dict


def mysql_execute_command(
        conn_mysql:pymysql.connections.Connection,
        file_content_dict:dict,
        sql_command_delimiter:str=';'
        ):
        """
        Executes SQL commands from files content in a MySQL database.

        Args:
            conn_mysql (pymysql.connections.Connection): A connection object for interacting with MySQL database.
            file_content_dict (dict): A dictionary containing file paths as keys and file contents as values.
            delimiter (str, optional): The delimiter used to separate SQL commands within files. Default is ';'.

        Returns:
            dict: A dictionary containing information about the execution.
        """
        errors = 0
        try:
            cursor = conn_mysql.cursor()
            for file_path in file_content_dict.keys():
                file_contents = file_content_dict[file_path]
                sql_commands = file_contents.split(';')
                for sql_command in sql_commands:
                    if sql_command.strip():  # Check if the command is not empty
                        cursor.execute(sql_command)
                        conn_mysql.commit()    
                print(f"Script '{file_path}' executed successfully")
        except Exception as e:
            errors += errors
            print(f"Error executing script '{file_path}': {e}")
            print(f"Error sql_command '{sql_command}'")
            conn_mysql.rollback()
        finally:
            cursor.close()
        
        return {
            "statusCode": 200,
            "body"      : f"Database file loaded into RDS MySQL with {errors} errors"
        }



def lambda_handler(event, context):
    """
    Handles the Lambda function.

    Args:
        event (dict): The event data passed to the Lambda function.
        context (object): The runtime information provided by AWS Lambda.

    Returns:
        dict: A dictionary containing information about the execution.

    Note:
        This function is designed to be used as an AWS Lambda function. It connects to AWS services
        such as CodeCommit, and RDS MySQL, retrieves files from CodeCommit, and executes SQL scripts
        to load data into an RDS MySQL database.
    """
    #### Parameters
    # CodeCommit
    repository_name = 'SourceRDS'
    branch_name = 'master'
    folderPath ='LambdaScripts/LoadEmployeesDB/SQL'

    # S3
    bucket_name = '000-create-store-build-resources'
    s3_key_prefix = ''

    # RDS MySQL DB
    rds_username, rds_password = get_secret(
        secret_name = "/source/db/cryptocurrency/password"
    )

    #### Initiate Connections
    # RDS MySQL DB
    conn_mysql = connect_to_mysql(
        host='sourcedbinstance.cdhvwedmmsgz.us-east-1.rds.amazonaws.com', 
        user=rds_username,
        password=rds_password,
        database='SourceDB'
        )
    
    # CodeCommit
    conn_codecommit = connect_to_codecommit()
    # S3
    conn_s3 = connect_to_s3()


    #### Move files from CodeCommit repo to Bucket S3
    # Get the list of all files within the specified CodeCommit repo path and branch.
    files_path = list_files_code_commit(
            conn_codecommit,
            repository_name,
            branch_name,
            folderPath
    )   
    # Get the files content and save it to dictionaries
    # A dictionary containing file paths as keys and file contents as values.
    file_content_dict = get_code_commit_files_content(
            conn_codecommit,
            repository_name,
            branch_name,
            files_path
    )
    
    # Execute SQL commands in the SQL Database
    response_execute_my_sql = mysql_execute_command(
        conn_mysql,
        file_content_dict
        )

    return response_execute_my_sql