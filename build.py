import csv
from platform import architecture
import shutil
import subprocess
import os
import tempfile
import argparse
import glob

### CM Doc

class doc_version:
    def __init__(self, ver : str) -> None:
        self.X = int(ver.split('.')[0])
        self.Y = int(ver.split('.')[1])
        self.Z = int(ver.split('.')[2])

    def __str__(self) -> str:
        return f'{self.X}.{self.Y}.{self.Z}'

class doc_configuration_items:
    def __init__(self, code : str, src_path : str, dest_path : str, version : str, explict_filname_version : bool) -> None:
        self.code = code
        self.src_path = src_path
        self.dest_path = dest_path
        self.version = doc_version(version)
        self.explict_filname_version = explict_filname_version

    def __str__(self) -> str:
        return f'{self.code};{self.src_path};{self.dest_path};{str(self.version)};{self.explict_filname_version}'

def _read_doc_config():
    config_items = []

    with open('config.csv', newline='\n') as config_database:
        csv_reader = csv.reader(config_database, delimiter=';')
        for c_item in csv_reader:
            config_items.append(
                doc_configuration_items(
                    c_item[0],
                    c_item[1],
                    c_item[2],
                    c_item[3],
                    bool(c_item[4])
                )
            )
    return config_items

def _write_doc_config(cis : list):
    with open('config.csv', newline='\n', mode='w') as config_database:
        for _,ci in enumerate(cis):
            config_database.write(str(ci))
            if _+1 != cis.__len__:
                config_database.write('\n')


def _move_doc(src_path, destination_path):
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    shutil.move(src_path, destination_path)


def _build_documents(doc_config_items : list, labels : list):
    for ci in doc_config_items:
        if not any('rebuild' in lb for lb in labels):
            if labels != None and not any(ci.code in lb for lb in labels):
                continue

            # Update doc version
            if any('enhancement' in lb for lb in labels):
                ci.version.Y += 1
            elif any('maintenance' in lb for lb in labels):
                ci.version.Z += 1

        print(f"\nBuilding {ci.code}\n")
        status = subprocess.run(['latexmk', '-pdf', '-cd', ci.src_path], cwd=os.getcwd())
        if(status.returncode != 0):
            exit(1)
        status = subprocess.run(['latexmk', '-c', '-cd', ci.src_path], cwd=os.getcwd())

        build_pdf_path = f'{ci.src_path.replace(os.path.basename(ci.src_path),'')}{os.path.basename(ci.src_path).split('/')[-1].split('.')[0]}.pdf'

        # Remove old vers
        for filename in glob.glob(f'{os.getcwd()}/{ci.dest_path}/{os.path.basename(ci.src_path).split('/')[-1].split('.')[0]}*.pdf'):
            print(filename)
            os.remove(filename)

        if ci.explict_filname_version == True:
            target_name = f'{os.path.basename(ci.src_path).split('/')[-1].split('.')[0]}_{str(ci.version)}.pdf'
        else:
            target_name = f'{os.path.basename(ci.src_path).split('/')[-1].split('.')[0]}.pdf'
        
        
        _move_doc(build_pdf_path, f'{os.getcwd()}/{ci.dest_path}/{target_name}')


def _cleanup_all_builds(doc_config_items : list):
    for ci in doc_config_items:
        shutil.rmtree(os.path.join(os.getcwd(), ci.dest_path.split('/')[0]), ignore_errors=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='QB Software CM and building tool'
    )
    parser.add_argument(
        '--labels', type=str
    )
    parser.add_argument(
        '--clean', action='store_true'
    )
    args = parser.parse_args()


    if args.labels == None:
        exit(1)

    labels = args.labels.split('\n')

    doc_cis = _read_doc_config()
    if any('documentation' in lb for lb in labels):
        _build_documents(doc_cis, labels)
    if args.clean:
        _cleanup_all_builds(doc_cis)
    _write_doc_config(doc_cis)
