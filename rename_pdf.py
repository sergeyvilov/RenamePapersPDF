#Rename pdf files of scientific papers
#Looks for all pdfs in a given directory and its subdirectories
#and gives them human-readable names based on their DOI

#Argument:  pdf file to rename or the directory to scan

import sys
import requests
import os
import fitz #PyMuPDF
import re
import time

RENAME_WITH_META_AUTORIZED = 0 #rename using meta data in the pdf if we can't find DOI (works badly)
DOI_BY_TITLE_AUTORIZED = 1 #if there's no DOI on the first page, get DOI from the paper's title
MINIMAL_FILE_NAME_LENGTH = 10 #minimal length of the new name

crossref = 'http://api.crossref.org/' #use crossref to get authors, year and title from DOI

#Check if a given file is a pdf
def IsPDF(file):

    if file.split('/')[-1].count('.pdf'):
        return True
    else:
        return False

#Scan a given directory for pdf files
def GetAllPDF(path):

    pdfs = []

    for root, d_names, files in os.walk(path):
        for file in files:
            if IsPDF(file):
                pdfs.append((root, file))

    return pdfs

#Get DOI using the paper's title
def GetDOIbyTile(title):

    query = crossref + 'works?query="{}"'.format(title)
    r = requests.get(query)

    try:

        item = r.json()

        first_result = item['message']['items'][0]
        doi = first_result['DOI']
        print('DOI: {}'.format(doi))
        return doi

    except:

        print('No DOI found')
        return None

#Remove from the proposed name symbols that are forbidden in file names
def CleanName(name):

    safe_name = ''

    name = name.replace(':', '.')

    for symbol in name:

        if (symbol in ['.', ' ', '-', ',', '(', ')'] or
            (symbol>='a' and symbol<='z') or
            (symbol>='A' and symbol<='Z') or
            (symbol>='0' and symbol<='9')):
            safe_name += symbol

    return safe_name

#remove last symbol that happens to be in DOI due to poor parsing/noise
def CleanDOI(doi):

    l = len(doi)

    while doi[l-1] in ['.', ';', '_', ':', '-']:
        l -= 1

    return doi[:l]

#get document information using DOI and compose the new name
def RenameWithDOI(doi):

    # def GetFullAuthorName(author):

      # given = author['given']
      # family = author['family']
      #
      # if given.count(' '):
      #     given = given[0] + '.' + given[given.find(' ')+1] + '.'
      # else:
      #     given = given[0] + '.'
      #
      # return family + ',' + given


    print('Renaming with DOI')

    url = '{}works/{}'.format(crossref, doi)
    r = requests.get(url)

    try:
        item = r.json()
    except:
        print('JSON ERROR. Incorrect DOI?')
        return None

    message = item['message']

    if not ('author' in message.keys() and
            'title' in message.keys() and 'created' in message.keys()):
            print('ERROR: AUTHOR or TITLE or CREATED fields not found for this DOI')
            return None

    title = message['title'][0]
    year = message['created']['date-parts'][0][0]

    authors = message['author']
    total_authors = len(authors)
    first_author = authors[0]['family']

    if total_authors == 2:

      second_author = authors[1]['family']
      authors = first_author + ', ' + second_author

    elif total_authors>2:

      authors = first_author + ' et al.'

    else:

      authors = first_author

    #new name format: author - year - title
    name = '{} - {} - {}'.format(authors, year,title)

    return CleanName(name)

#Rename the pdf using the paper's meta information
def RenameWithMETA(meta):

    print('Renaming with pdf meta information')

    if ('author' in meta.keys() and
        'title' in meta.keys()):

        author = meta['author']
        title = meta['title']

        name = author + '. ' + title
        return CleanName(name)

    else:

        print('ERROR: AUTHOR or TITLE fields not found in meta')
        return None

def GetNewName(pdf):

    meta = pdf.metadata

    #First try to get DOI from the paper's meta
    if 'doi' in meta.keys():

        doi = meta['doi']

        print('DOI found in the pdf meta. DOI: {}'.format(doi))

    else: #if DOI is not in the paper's meta data

        #sometimes DOI is printed on the 1st page
        print('Trying to get DOI from the first page content')

        first_page = pdf.loadPage(0).getText()

        doi =  re.search(r'10.\d{4,9}/[-._;()/:\w0-9]+', first_page)         #https://www.crossref.org/blog/dois-and-matching-regular-expressions/

        if not doi:

            doi = re.search(r'10.1002/[^\s]+', first_page)

        if doi:

            doi = doi.group(0)

            doi = CleanDOI(doi)

            print('DOI: {}'.format(doi))

        else: #if DOI isn't found on the 1st page

            print('No DOI-like information found on the first page')

            if DOI_BY_TITLE_AUTORIZED:
                #use paper's title to search for DOI on crossref
                print('Searching for DOI by title')

                if 'title' in meta.keys() and meta['title'] != None:

                    print(meta['title'])
                    doi = GetDOIbyTile(meta['title'])

                else:

                    print('No title in meta data')

    new_name = None

    try:
       new_name = RenameWithDOI(doi)
    except:
       try:
           if RENAME_WITH_META_AUTORIZED:
               new_name = RenameWithMETA(meta)
       except:
           return None

    if new_name and len(new_name)<MINIMAL_FILE_NAME_LENGTH:
        print('Suggested file name is too short: {}.pdf'.format(new_name))
        return None

    return new_name

if __name__ == '__main__':

    total_files = 0
    total_renamed = 0

    argv = sys.argv[1]

    if IsPDF(argv):
        #1st argument - pdf file to rename
        pdfs = [('', argv)]
    else:
        #1st argument - directory to scan for pdfs
        pdfs = GetAllPDF(argv)

    total_files = len(pdfs)

    new_names = []

    for pdf in pdfs:

        root = pdf[0]
        old_name = pdf[1]

        print('Trying to rename:\n{}'.format(os.path.join(root, old_name)))

        pdf = fitz.open(os.path.join(root, old_name))

        new_name_base = GetNewName(pdf)

        if new_name_base:

            if os.path.join(root, new_name_base+'.pdf') in new_names:
                n = re.search('(.+?)_([0-9]+)$',new_name_base)
                if n:
                    new_name_base,count = n.groups(1)
                    count = int(count)
                    while os.path.join(root, new_name_base+'_'+str(count)+'.pdf') in new_names:
                        count += 1
                    new_name_base = new_name_base + '_' + str(count)
                else:
                    new_name_base = new_name_base + '_2'

            new_name = new_name_base + '.pdf'

            try:
                print('New name: {}'.format(new_name))
                temporary_name = os.path.join(root, new_name+'.tmp') #first we create tmp files and then rename them to pdf
                os.rename(os.path.join(root, old_name), temporary_name)
                while not os.path.exists(temporary_name):
                    time.sleep(0.25) #wait until file is really on the disk
                total_renamed += 1
                print('Total renamed: {}/{}\n'.format(total_renamed, total_files))
                new_names.append(os.path.join(root, new_name))
            except Exception as e:
                print('Error during renaming:')
                print(e)
                print('Not renamed\n')

        else:

            print('Not renamed\n')

for new_name in new_names:
    os.rename(new_name+'.tmp', new_name) #.tmp-->.pdf
    while not os.path.exists(new_name):
        time.sleep(0.25)

print('Total files processed: {}'.format(total_files))
print('Total files renamed: {}'.format(total_renamed))
