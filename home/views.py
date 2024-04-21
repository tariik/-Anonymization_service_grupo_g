import os
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from home.anonymization import process_input_database, process_anonymized_database


# Home page view
def home_view(request):
    return render(request, "home.html")

# Upload view
def upload_view(request):
    if request.method == 'POST' and request.FILES['file']:
        file = request.FILES['file']                                        # Get the upload data file
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)                                 # Save the file
        file_path = fs.path(filename)
        processed_data = process_input_database(file_path)                  # Process the data to anonymize
        if processed_data == None:
            print('Data without the correct structure to anonymize.')
            return render(request, "upload.html")
        
        if processed_data['database'] == 'customers':                       # Customers database context to pass to the view
            context = {
                'customer_list_orig': processed_data['original'],           # Original dataset
                'customer_list_anon': processed_data['anonymized'],         # Anonymized dataset
                'filename': filename,                                       # Original file name
                'filename_anon': 'anonymized_'+filename,                    # Anonymized dataset
                'key_filename': filename.replace('.csv', '.enc')            # Decryption key file name
            }
        else:                                                               # Airline passengers database context to pass to the view
            context = {
                'passengers_list_orig': processed_data['original'],         # Original dataset
                'passengers_list_anon': processed_data['anonymized'],       # Anonymized dataset
                'filename': filename,                                       # Original file name
                'filename_anon': 'anonymized_'+filename,                    # Anonymized dataset
                'key_filename': filename.replace('.csv', '.enc')            # Decryption key file name
            }
        return render(request, 'result.html', context)                      # Load result page
    else:
        return render(request, "upload.html")                               # GET request: Load upload page

# Revert view
def revert_view(request):
    if request.method == 'POST' and request.FILES['file-data'] and request.FILES['file-key']:
        file_data = request.FILES['file-data']                              # Get the upload data file
        file_key = request.FILES['file-key']                                # Get the upload key file

        fs = FileSystemStorage()
        filename_data = fs.save(file_data.name, file_data)                  # Save data file
        file_path = fs.path(filename_data)
        filename_key = fs.save(file_key.name, file_key)                     # Save key file
        key_path = fs.path(filename_key)

        processed_data = process_anonymized_database(file_path, key_path)   # De-anonymize data

        if processed_data == None:
            print('Data without the correct structure to anonymize.')
            return render(request, "upload.html")
        
        filename = 'recovered_'+ filename_data.replace('anonymized_', '')   # Create file name for recovered file
        if processed_data['database'] == 'customers':                       # Customers database context to pass to the view
            context = {
                'customer_list_orig': processed_data['original'],           # Original dataset
                'customer_list_anon': processed_data['anonymized'],         # Anonymized dataset
                'filename': filename                                        # Recovered dataset file name
            }
        else:                                                               # Airline passengers database context to pass to the view
            context = {
                'passengers_list_orig': processed_data['original'],         # Original dataset
                'passengers_list_anon': processed_data['anonymized'],       # Anonymized dataset
                'filename': filename                                        # Recovered dataset file name
            }
        return render(request, 'result_reverted.html', context)             # Load reverted result page
    else:
        return render(request, "revert.html")                               # GET request: Load revert page