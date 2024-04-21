import pandas as pd
import os
from cryptography.fernet import Fernet
import json
import base64
import numpy as np
from collections import defaultdict

def process_input_database(file):
    df = pd.read_csv(file)                                          # Convert file in pandas data frame

    db = check_database(df)                                         # Check that dataset is of shop customers of airline passengers
    if db == '': return
    
    original = df.to_dict('records')                                # Save original data to show in view

    key = generate_key(file)                                        # Generate encryption key
    df = remove_identifiers(df, key)                                # Remove identifiers of the dataset
    
    # FUNCIONES DE ANNONYMIZACIÓN A APLICAR 

    df = generalize_age(df)
    df = generalize_gender(df)

    if db == 'airlines':
        df = perturbation_distance(df)
        df = generalize_class(df)
        df = realizarK(df)
        # FALTA Supression       

    if db == 'customers':
        #df = perturbation_income(df)
        df = generalize_profession(df)      
        df['Family_Size'] = permute(df['Family_Size'].values)
        #df = realizarK2(df)
        # apply l-diversity to the dastaset
        df = l_diversity(df, 'Annual_Income', 'Age', 2)
        df = t_closeness(df, 'Age', t=0.1)

    anonymized = df.to_dict('records')                              # Save anonymized data to show in view

    save_anonymized_database(df, file)                              # Save anonymized data to file

    return {
        'database': db,
        'original': original,
        'anonymized': anonymized
    }

def process_anonymized_database(file_data, file_key):
    df = pd.read_csv(file_data)                                     # Convert file in pandas data frame

    db = check_database(df)                                         # Check that dataset is of shop customers of airline passengers
    if db == '': return
    
    anonymized = df.to_dict('records')                              # Save original data to show in view

    key = read_file(file_key)                                       # Read uploaded encryption key
    df = add_identifiers(df, key)                                   # Decrypt identifiers and set the original ones

    original = df.to_dict('records')                                # Save original data to show in view

    save_recovered_database(df, file_data)                          # Save recovered data to file

    return {
        'database': db,
        'original': original,
        'anonymized': anonymized
    }


def check_database(df):
    print(df)
    if "Spending_Score" in df.columns:                              # When the header includes a "Spending score", it is the customer database.
        return 'customers'
    elif "satisfaction" in df.columns:                              # When the header includes the "satisfaction" is from airline passangers
        return 'airlines'
    else:
        print("File has not predefined structure to anonymize")     # Otherwise, it does not read
        return ''

def generate_key(file):
    key = os.urandom(32)                                            # Generate random key
    
    directory, filename = os.path.split(file)
    new_path = os.path.join(directory,
                            filename.replace('.csv', '.enc'))
    write_file(new_path, key)                                       # Save key to a file
    return key

def encrypt_data(data, key):                                        # Data encryption fucntion
    key = base64.urlsafe_b64encode(key)
    f = Fernet(key)
    ciphertext_data = f.encrypt(json.dumps(data.decode('utf-8')).encode('utf-8'))               
    return ciphertext_data

def decrypt_data(ciphertext, key):                                  # Data decryption fucntion
    key = base64.urlsafe_b64encode(key)
    f = Fernet(key)
    plaintext = f.decrypt(ciphertext)
    return plaintext

def remove_identifiers(df, key):                                    # Function to remove the identifiers (CustomerID) of the dataset by encryption
    # Encrypt the "CustomerID" column
    encrypted_customer_id = df['CustomerID'].apply(lambda x: encrypt_data(str(x).encode('utf-8'), key))
    df['CustomerID'] = encrypted_customer_id.apply(lambda x: x.decode('utf-8'))
    
    # Return the encrypted data and the key
    return df

def add_identifiers(df, key):                                    # Function to decrypt the identifiers (CustomerID) of the dataset to get the original ones

    # Decrypt the "CustomerID" column
    decrypted_customer_id = df['CustomerID'].apply(lambda x: decrypt_data(x, key))
    df['CustomerID'] = [int(x.decode('utf-8').replace('"','')) for x in decrypted_customer_id]
    
    # Return the data frame with the identifiers added back
    return df

def generalize_age(df):                                           # Function to generalize age
    general_age = df['Age'].apply(lambda x: validate_age(x))
    df['Age'] = general_age
    return df

def validate_age(age):                                            # Function to validate age into range
    if age < 20:
        return "< 20"
    elif age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    else:
        return ">= 50" 
    
def generalize_gender(df):                                        # Function to generalize age
    anon_dict = {
        'Male': 'Male/Female',
        'Female': 'Male/Female',
        '': 'Other/No binario'
    }
    df['Gender'] = df['Gender'].map(anon_dict)                           
    return df  

def perturbation_distance(df):                                                                              # Function to perturb distance with microaggregation
    num_groups = 3
    group_distance = df['Flight_Distance'].quantile(np.linspace(0, 1, num_groups+1))                        # Divide groups of the same size 
    print("group_income\n",group_distance)
    df['aggregate_distance'] = pd.cut(df['Flight_Distance'], group_distance, labels=False, right=False)     # Asing a group value to each flight distance
    df['Flight_Distance'] = df.groupby('aggregate_distance')['Flight_Distance'].transform('mean').round(2)  # Replace each distance to group mean

    return df

def perturbation_income(df):                                            # Function to perturb income adding noise
    perturb_income = df['Annual_Income'].apply(lambda x: x + round(np.random.normal(scale=1000),1))
    df['Annual_Income'] = perturb_income
    return df

def permute(x):                                                         # Function to permute 
    perm = np.random.permutation(len(x))
    return x[perm]

def generalize_profession(df):                                          # Define dictionary for Semantic generalization: of "profession"
    anon_dict = {
        'Healthcare': 'Health',
        'Executive': 'Business',
        'Engineer': 'Engineer',
        'Lawyer': 'Legal',
        'Entertainment': 'Art',
        'Artist': 'Art',
        'Doctor': 'Health',
        'Marketing': 'Business',
        'Homemaker': 'Other',
        '': 'Otro'
    }
    df['Profession'] = df['Profession'].map(anon_dict)                  # Apply anonimization to "Profession"
    return df

def realizarK(df):

    # Agrupar los datos por las columnas "Age", "Class" y "Flight_Distance"
    groups = df.groupby(["Age", "Class", "Flight_Distance"])

    # Crear un nuevo dataframe con los grupos de 3 elementos
    df_grouped = pd.DataFrame(columns=df.columns)
    for _, group in groups:
        if len(group) >= 3:
            df_grouped = pd.concat([df_grouped, group[:3]])
        else:
            df_grouped = pd.concat([df_grouped, group])

    # Eliminar los grupos que no tienen al menos 2 elementos
    df_grouped = df_grouped.groupby(["Age", "Class", "Flight_Distance"]).filter(lambda x: len(x) >= 2)

    return df_grouped


def realizarK2(df):


    # Agrupar los datos por las columnas "Age", "Class" y "Flight_Distance"
    groups = df.groupby(["Age",'Annual_Income', 'Profession'])

    # Crear un nuevo dataframe con los grupos de 3 elementos
    df_grouped = pd.DataFrame(columns=df.columns)
    for _, group in groups:
        if len(group) >= 3:
            df_grouped = pd.concat([df_grouped, group[:3]])
        else:
            df_grouped = pd.concat([df_grouped, group])

    # Eliminar los grupos que no tienen al menos 2 elementos
    df_grouped = df_grouped.groupby(["Age",'Annual_Income', 'Profession']).filter(lambda x: len(x) >= 2)

    return df_grouped



def generalize_class(df):                                               # Define dictionary for masking of "Class"
    anon_dict = {
        'Eco': 'Eco*****',
        'Business': 'Bus*****',
        'Eco Plus': 'Eco*****',
        '': 'Other'
    }
    df['Class'] = df['Class'].map(anon_dict)                            # Aplicar anonimización a la columna "Profesión"
    return df

def save_anonymized_database(df, file):                                 # Save the anonymized list file for later downloading
    directory, filename = os.path.split(file)
    new_path = os.path.join(directory, 'anonymized_'+filename)
    df.to_csv(new_path, index=False)

def save_recovered_database(df, file):                                 # Save the anonymized list file for later downloading
    directory, filename = os.path.split(file)
    new_path = os.path.join(directory, 'recovered_'+filename.replace('anonymized_', ''))
    df.to_csv(new_path, index=False)

def write_file(filename, content):                                      # Write a new file by the file name and content
    with open(filename, 'wb') as f:
        f.write(content)

def read_file(filename):                                                # Read a file by the file name
    with open(filename, 'rb') as f:
        data = f.read()
    
    return data

def l_diversity(df, sensitive_column, diversity_column, l):
    """
    Applies l-diversity to a dataset by replacing values in the sensitive column with a
    randomly selected value that satisfies l-diversity.

    Args:
        df (pandas.DataFrame): the dataset to be anonymized
        sensitive_column (str): the name of the sensitive column in the dataset
        diversity_column (str): the name of the column that represents the diversity attribute
        l (int): the minimum required number of distinct values in the sensitive column for each group

    Returns:
        A new anonymized dataset with l-diversity applied
    """
    groups = df.groupby(diversity_column)
    new_df = pd.DataFrame(columns=df.columns)

    for _, group in groups:
        if len(group) < l:
            new_df = pd.concat([new_df, group])
            continue

        sensitive_values = group[sensitive_column].values
        unique_values, value_counts = np.unique(sensitive_values, return_counts=True)

        if len(unique_values) >= l:
            new_df = pd.concat([new_df, group])
            continue

        sensitive_dict = defaultdict(list)
        for i, value in enumerate(sensitive_values):
            sensitive_dict[value].append(i)

        for value, indexes in sensitive_dict.items():
            if len(indexes) >= l:
                new_df = pd.concat([new_df, group.iloc[indexes]])
            else:
                remaining_indexes = np.random.choice(indexes, size=l - len(indexes), replace=True)
                selected_indexes = np.concatenate([indexes, remaining_indexes])
                new_df = pd.concat([new_df, group.iloc[selected_indexes]])

    return new_df


def t_closeness(df, sensitive_column, t=0.2):
    """
    Anonymize a dataframe using the t-closeness technique.

    Parameters:
    df (pandas.DataFrame): The dataframe to anonymize.
    sensitive_column (str): The name of the sensitive column in the dataframe.
    t (float): The t-closeness threshold. Default is 0.2.

    Returns:
    pandas.DataFrame: The anonymized dataframe.
    """

    # Create a dictionary of values for the sensitive column
    sensitive_dict = defaultdict(list)
    for i, row in df.iterrows():
        sensitive_dict[row[sensitive_column]].append(i)

    # Calculate the global frequency of each sensitive value
    freq = df[sensitive_column].value_counts(normalize=True)

    # Create a mapping of sensitive values to their frequency rank
    rank = {}
    for i, s in enumerate(freq.index):
        rank[s] = i

    # Anonymize the sensitive column for each group of rows with the same value
    for s, rows in sensitive_dict.items():
        group_size = len(rows)
        group_freq = freq[s]
        max_distance = 0

        # Calculate the maximum distance between the group's distribution and the global distribution
        for j, s2 in enumerate(freq.index):
            if s2 == s:
                continue
            dist = abs(freq[s2] - group_freq)
            if dist > max_distance:
                max_distance = dist

        # Anonymize the sensitive column for this group
        if max_distance > t:
            # If the maximum distance is greater than the threshold, use generalization
            for i in rows:
                df.at[i, sensitive_column] = np.random.choice(freq.index)
        else:
            # Otherwise, use suppression
            for i in rows:
                df.at[i, sensitive_column] = np.nan

    # Fill in the suppressed values with generalization
    df[sensitive_column].fillna(value=np.random.choice(freq.index), inplace=True)

    return df