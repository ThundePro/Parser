import os
import shutil
import requests
from bs4 import BeautifulSoup
import zipfile
import hashlib
import json


class Voip:
    models = None

    def __init__(self, models):
        self.models = models


class Product:
    model = None
    vendor = 'grandstream'
    version = None
    zip_file = None
    files = None

    def __init__(self, model, version, zip_file=None, files=None):
        if model == '4024':
            model = 'GXW' + model
            version = '1.0.12.4'
        elif model == 'BT200':
            model = 'GXP1200'
        self.model = model
        self.version = version

        if zip_file is None:
            self.zip_file = 'None zip file'
        elif zip_file[0] == '/':
            zip_file = "https://www.grandstream.com" + zip_file
        self.zip_file = zip_file
        if files is None:
            self.files = []
        else:
            self.files = files

    def __eq__(self, other):
        if isinstance(other, Product):
            return self.model == other.model
        return False

    def __str__(self):
        return f'{self.model} : {self.version}\n' \
               f'{self.files}\n'

    def add_file(self, file):
        self.files.append(file)

    # def deserializable(self, model, vendor, version, files):
    #     return Product(model, version, None)


# Clean the list
def screening(array):
    check_list = ['GXP16xx', 'GXP2130', 'GXP2140', 'GXP2160', 'GXW4024', 'GXW4216', 'GXW4216v2', 'GXW4224', 'GXW4224v2',
                  'GXW4232', 'GXW4248', 'HT801', 'HT802', 'HT813', 'HT818', 'HT812', 'HT814', 'GXP116x', 'GXP1200',
                  'GXP140x', 'GXP1450', 'GXW4008', 'HT502', 'HT702', 'HT704']
    new_array = []
    for obj in array:
        if obj.model in check_list:
            obj.model = [obj.model]
            tmp = obj
            if tmp in new_array:
                continue
            # elif tmp.model[0] == 'GXP16xx':
            #     tmp.model[0] = 'GXP1600'
            # elif tmp.model[0] == 'GXP116x':
            #     tmp.model[0] = 'GXP1160'
            # elif tmp.model[0] == 'GXP140x':
            #     tmp.model[0] = 'GXP1400'
            # else:
            #     obj.model = [obj.model]
            new_array.append(tmp)
    return new_array


def addition(products):
    full_models = {
        'GXP16xx': ['GXP1610', 'GXP1615', 'GXP1620', 'GXP1625', 'GXP1628', 'GXP30'],
        'GXP116x': ['GXP1160', 'GXP1165'],
        'GXP140x': ['GXP1400', 'GXP1405']
    }
    for prod in products:
        for key, value in full_models.items():
            if prod.model[0] == key:
                prod.model = value
    return products


def get_html():
    url = "https://www.grandstream.com/support/firmware"
    response = requests.get(url)

    html = response.content
    soup = BeautifulSoup(html, 'lxml')
    return soup.find_all('a')


# Get all link in html page
def get_products():
    array = []
    mass = get_html()
    for link in mass:
        tmp_link = link.get('href')
        if tmp_link[len(tmp_link) - 4:] == '.zip':
            split_link = tmp_link.split('_')
            vers = split_link[-1][:-4]
            if len(split_link) == 3:
                names = split_link[1]
                array.append(Product(names, vers, tmp_link))
            else:
                names = split_link[1:len(split_link) - 1]
                for name in names:
                    array.append(Product(name, vers, tmp_link))
    return array


# Download files which have extension .zip
def download_file(array):
    for prod in array:
        response = requests.get(prod.zip_file)
        with open(prod.model[0] + '.zip', 'wb') as f:
            f.write(response.content)
        print(prod.zip_file, '- successfully')


# Unzip file, get hash file and write result to list
def unzip_files(array):
    for prod in array:
        with zipfile.ZipFile(prod.model[0] + '.zip', 'r') as zip_ref:
            file_names = zip_ref.namelist()
            if len(file_names) > 5:
                for name in file_names:
                    zip_ref.extract(name)
                    prod.add_file({name: get_hash(name)})
                    os.remove(name)
            elif len(file_names) == 5:
                zip_ref.extract(file_names[4])
                zip_ref.extract(file_names[2])
                prod.add_file({file_names[4].split('/')[-1]: get_hash(file_names[4])})
                prod.add_file({file_names[2].split('/')[-1]: get_hash(file_names[2])})
                for file in file_names:
                    try:
                        os.remove(file)
                    except PermissionError:
                        shutil.rmtree(file)
                    except FileNotFoundError:
                        pass
            else:
                zip_ref.extract(file_names[-1])
                prod.add_file({file_names[-1].split('/')[-1]: get_hash(file_names[-1])})
                for file in file_names:
                    try:
                        os.remove(file)
                    except PermissionError:
                        shutil.rmtree(file)
                    except FileNotFoundError:
                        pass
        try:
            os.remove(prod.model[0] + '.zip')
        except PermissionError:
            shutil.rmtree(prod.model[0] + '.zip')
        except FileNotFoundError:
            pass
    return array


# Create hash md5
def get_hash(file_name):
    with open(file_name, 'rb') as f:
        data = f.read()
        hasher = hashlib.md5()
        hasher.update(data)
        return hasher.hexdigest()


products = get_products()
clear_list = screening(products)
download_file(clear_list)
list_for_json = unzip_files(clear_list)
full_models = addition(list_for_json)
voip_dict = {
    'voip': [
        {
            "model": obj.model,
            "vendor": obj.vendor,
            "version": obj.version,
            "files": obj.files
        } for obj in full_models
    ]
}
with open("DataBase.json", 'w') as file:
    json.dump(voip_dict, file)

with open("DataBase.json", 'r') as file:
    deserialized_dict = json.load(file)

deserialized_product = [Product(item_dict['model'], item_dict['version'], None, item_dict['files'])
                        for item_dict in deserialized_dict['voip']]
voip = Voip(deserialized_product)
for prod in voip.models:
    print(prod)
