import os

import requests
from bs4 import BeautifulSoup
import zipfile
import hashlib
import json


class ProductEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Product):
            return {"model": obj.model, "vendor": obj.vendor, "version": obj.version, "files": obj.files}
        return super().default(obj)


class Product:
    model = None
    vendor = 'grandstream'
    version = None
    zip_file = None
    files = None

    def __init__(self, name, version, zip_file=None):
        if name == '4024':
            name = 'GXW' + name
            version = '1.0.12.4'
        elif name == 'BT200':
            name = 'GXP1200'
        self.model = name
        self.version = version
        if zip_file[0] == '/':
            zip_file = "https://www.grandstream.com" + zip_file
        self.zip_file = zip_file
        self.files = []

    def __eq__(self, other):
        if isinstance(other, Product):
            return self.model == other.model
        return False

    def __str__(self):
        return f'{self.model} : {self.version} - {self.zip_file}\n' \
               f'{self.files}'

    def add_file(self, file):
        self.files.append(file)


def screening(array):
    check_list = ['GXP16xx', 'GXP2130', 'GXP2140', 'GXP2160', 'GXW4024', 'GXW4216', 'GXW4216v2', 'GXW4224', 'GXW4224v2',
                  'GXW4232', 'GXW4248', 'HT801', 'HT802', 'HT813', 'HT818', 'HT812', 'HT814', 'GXP116x', 'GXP1200',
                  'GXP140x', 'GXP1450', 'GXW4008', 'HT502', 'HT702', 'HT704']
    new_array = []
    for obj in array:
        if obj.model in check_list:
            if obj in new_array:
                continue
            new_array.append(obj)
    return new_array


def get_html():
    url = "https://www.grandstream.com/support/firmware"
    response = requests.get(url)

    html = response.content
    soup = BeautifulSoup(html, 'lxml')
    return soup.find_all('a')


def get_products():
    array = []
    for link in get_html():
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


def download_file(array):
    for prod in array:
        response = requests.get(prod.zip_file)
        with open(prod.model + '.zip', 'wb') as f:
            f.write(response.content)
        print(prod.model + '.zip', '- successfully')


def unzip_files(array):
    for count in range(0, len(array)):
        with zipfile.ZipFile(array[count].model + '.zip', 'r') as zip_ref:
            file_names = zip_ref.namelist()
            if len(file_names) > 5:
                for name in file_names:
                    zip_ref.extract(name)
                    array[count].add_file({name: get_hash(name)})
                    os.remove(name)
            elif len(file_names) == 5:
                zip_ref.extract(file_names[4])
                zip_ref.extract(file_names[2])
                array[count].add_file({file_names[4].split('/')[-1]: get_hash(file_names[4])})
                array[count].add_file({file_names[2].split('/')[-1]: get_hash(file_names[2])})
                for file in file_names:
                    try:
                        os.remove(file)
                    except PermissionError:
                        print(f"File: {file} can`t remove")
            else:
                zip_ref.extract(file_names[-1])
                array[count].add_file({file_names[-1].split('/')[-1]: get_hash(file_names[-1])})
                for file in file_names:
                    try:
                        os.remove(file)
                    except PermissionError:
                        print(f"File: {file} can`t remove")
        try:
            os.remove(array[count].model + '.zip')
        except PermissionError:
            print(f'File: {array[count].model + ".zip"} can`t remove')
    return array


def get_hash(file_name):
    with open(file_name, 'rb') as f:
        data = f.read()
        hasher = hashlib.md5()
        hasher.update(data)
        return hasher.hexdigest()


clear_list = screening(get_products())
download_file(clear_list)
result = unzip_files(clear_list)
with open("DataBase.json", 'w') as outfile:
    json.dump(result, outfile, cls=ProductEncoder)
