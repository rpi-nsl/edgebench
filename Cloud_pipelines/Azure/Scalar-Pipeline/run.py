import os

# read the file uploaded into blob storage
inputMessage = open(os.environ['myBlob']).readline()
message = "Python script processed queue message"
print(message)

# Output the un-modified file to a separate folder in the Storage Blob
output_file = open(os.environ['outputBlob'], 'w')
output_file.write(inputMessage)
output_file.close()

            
