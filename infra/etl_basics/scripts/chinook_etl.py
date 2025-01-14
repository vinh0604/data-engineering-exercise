import sys
import boto3
import psycopg2
from awsglue.utils import getResolvedOptions
from datetime import datetime

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'DB_ENDPOINT', 
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'OUTPUT_BUCKET'
])

# Database connection
db_config = {
    'host': args['DB_ENDPOINT'],
    'database': args['DB_NAME'],
    'user': args['DB_USER'],
    'password': args['DB_PASSWORD']
}

# S3 client
s3 = boto3.client('s3')
bucket_name = args['OUTPUT_BUCKET']

def extract_table(table_name):
    try:
        # Connect to PostgreSQL
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()
        
        # Query data
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get column names
        colnames = [desc[0] for desc in cursor.description]
        
        # Write to S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_key = f"chinook/{table_name}/{timestamp}_{table_name}.csv"
        
        # Convert to CSV format
        csv_data = ",".join(colnames) + "\n"
        csv_data += "\n".join([",".join(map(str, row)) for row in rows])
        
        s3.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=csv_data
        )
        
        print(f"Extracted {len(rows)} rows from {table_name}")
        
    except Exception as e:
        print(f"Error processing {table_name}: {str(e)}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def main():
    # List of tables to extract
    tables = [
        'Album',
        'Artist',
        'Customer',
        'Employee',
        'Genre',
        'Invoice',
        'InvoiceLine',
        'MediaType',
        'Playlist',
        'PlaylistTrack',
        'Track'
    ]
    
    for table in tables:
        extract_table(table)

if __name__ == "__main__":
    main()
