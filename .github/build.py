import csv
from platform import architecture
import shutil
import subprocess
import os
import argparse
import glob
import datetime


# definisce i behaviour per la versione dei file
class doc_version:
    def __init__(self, ver : str) -> None:
        self.X = int(ver.split('.')[0])
        self.Y = int(ver.split('.')[1])
        self.Z = int(ver.split('.')[2])

    def __str__(self) -> str:
        return f'{self.X}.{self.Y}.{self.Z}'

# definisce i behaviour per i configuration items
class doc_configuration_items:
    def __init__(self, code : str, src_path : str, dest_path : str, version : str, explict_filname_version : bool) -> None:
        self.code = code
        self.src_path = src_path
        self.dest_path = dest_path
        self.version = doc_version(version)
        self.explict_filname_version = explict_filname_version

    def __str__(self) -> str:
        return f'{self.code};{self.src_path};{self.dest_path};{str(self.version)};{self.explict_filname_version}'


# ritorna true se il documento è un verbale
def _is_verbale(code_ci : str):
    return len(code_ci) >= 2 and (code_ci[0:2] == 'VI' or code_ci[0:2] == 'VE')


# ritorna il codice identificativo del documento
def _get_code(code_ci : str):
     return code_ci[0:2]


# ritorna il numero di serie del verbale
def _get_serial(code_ci : str):
    serial = code_ci[2:]
    if serial == '' or serial == None:
        return None
    else:
        return int(serial)
        
        
# ritorna la lista dei configuration items letti dal file csv
def _read_doc_config():
    config_items = []

    with open('.github/config.csv', newline='\n') as config_database:
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


# scrive sul csv gli update apportati ai configuration item 
def _write_doc_config(cis : list):
    with open('.github/config.csv', newline='\n', mode='w') as config_database:
        for _,ci in enumerate(cis):
            config_database.write(str(ci))
            if _+1 != cis.__len__:
                config_database.write('\n')


# sposta il file, nel path di destinazione
def _move_doc(src_path, destination_path):
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    shutil.move(src_path, destination_path)
    
    
#ritorna il path del changelog del file, dando come parametro il src del .tex
def _cl_path(text):
    list = text.split("/")
    path =""
    for i in range(len(list)-1):
        path = path + list[i] +"/"
    path = path + "changelog.tex" 
    return path

  
#scrive sul changelog una nuova riga per l'appovazione da parte del responsabile
def _update_cl_milestone_docs(file_path, admin_name, version):
    
    file_path = _cl_path(file_path)
    date = datetime.datetime.now()
    today = str(date.day) + "/" + str(date.month) + "/" + str(date.year)
    
    text_to_write = "\\milestone{"+ str(version) +"}{"+ today +"}{"+ admin_name +"}"
    word_to_seek = "{changelog}"
 
    with open(file_path, 'r') as file:
        contenuto = file.readlines()
        file.close()

    res =  ""
    found = False    
    for line in contenuto:
        if line.find(word_to_seek) != -1 and not found:
            res += line + "\t" + text_to_write + "\n"
            found = True
            continue
        res += line 
        
    with open(file_path, "w") as f:
        f.write(res)


# ritorna  il numero di serie dei verbale mancante
def _find_serial_numb(code):
    
    with open('.github/config.csv', "r") as f:
        ci = f.readlines()
        f.close()
    
    # extract verbals serials
    ci_verb_code = []
    list_of_serial = []
    for i, l in enumerate(ci):
        if code in l[0:4]:
            curr_line = ci[i].split(";")
            ci_verb_code.append(curr_line[0])
            list_of_serial.append(ci_verb_code[-1][2:])
          
    numbers =[]
    for i in range(len(list_of_serial)):
        if(list_of_serial[i]!=''):
            numbers.append(int(list_of_serial[i]))
        else:
            list_of_serial[i] = -1
            numbers.append(int(list_of_serial[i]))

    index = numbers.index(-1)
    index += 1
    
    if index<10:
        serial = "0" + str(index)
    else:
        serial = str(index)
    
    return serial


#ritorna il nome del file dando come parametro il path
def _get_file_name(path):
    list = path.split("/")
    name = list[-1]
    return name[:-4]
    
            
#aggiorna l'html cambiando il nome e la versione del file compilato          
def _update_html(src_path, version):
    
    with open("index.html","r") as file:
        lines = file.readlines()
        file.close()

    file_name = _get_file_name(src_path)
    
    index_of_line = -1
    for i, l in enumerate(lines):
        if file_name in l:
            line = lines[i]
            index_of_line = i
            break
        
    
    index_name = line.find(file_name)
    pdf_name =line[index_name:index_name+(len(file_name))+6]   
    
    v_tag = "version\">V"
    index_v = line.find(v_tag)
    old_version = line[index_v:index_v+len(v_tag)+5]
    
    new_version = v_tag + version
    new_pdf_name = file_name + "_" + version
    
    new_line = line.replace(pdf_name,new_pdf_name).replace(old_version,new_version)


    lines[index_of_line] = new_line
    
    with open("index.html", "w") as file:
        for i in range(len(lines)):
            file.write(lines[i])
 

# compila i documenti in base alle labels
def _build_documents(doc_config_items : list, labels : list):
    compiled_docs = 0

    for ci in doc_config_items:
        
        is_verbale = _is_verbale(ci.code)
        code : str
        serial : str
        
        if(is_verbale):
            code = _get_code(ci.code)
            serial = _get_serial(ci.code)

        if not any('rebuild' in lb for lb in labels):
            if not any('milestone' in lb for lb in labels) and not any(ci.code in lb for lb in labels):
                continue

            # Update doc version
            if any('milestone' in lb for lb in labels):
                ci.version.X += 1
                ci.version.Y = 0
                ci.version.Z = 0
                if any('admin:' in lb for lb in labels):
                    lab = ''.join(labels)
                    index = lab.find('admin:')
                    resp_name = lab[index + len('admin:'):]
                    _update_cl_milestone_docs(ci.src_path, resp_name, ci.version)
                else:
                    print("Manca il nome del responsabile")
                    exit(1)
            elif any('enhancement' in lb for lb in labels):
                ci.version.Y += 1
                ci.version.Z = 0      
            elif any('maintenance' in lb for lb in labels):
                ci.version.Z += 1
            else:
                print("Nessuna lables per l'avanzamento del documento è stata trovata")
                exit(1)

        _update_html(ci.src_path, str(ci.version))
        
        if(serial == None):
            serial = _find_serial_numb(code)
            ci.code = code + serial

        print(f"\nBuilding {ci.code}\n")
        status = subprocess.run(['latexmk', '-pdf', '-cd', ci.src_path], cwd=os.getcwd())
        if(status.returncode != 0):
            exit(1)
        status = subprocess.run(['latexmk', '-c', '-cd', ci.src_path], cwd=os.getcwd())

        compiled_docs += 1
        
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

    if compiled_docs == 0:
        print("Lables del documento da compilare non trovate")
        exit(1)
        
        
# toglie la polvere dalla build
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
