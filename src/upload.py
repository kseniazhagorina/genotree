#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['create_package']

import shutil
import os.path
import codecs
import hashlib
import re
from common_utils import first_or_default, convert_to_utf8, create_folder
from geddate import GedDate

# Загрузка базы данных и дерева единым пакетом
# Внутри:
# tree.ged - выгрузка в формате gedcom
# tree_img.svg - картинка с деревом в svg формате
# tree_img.svg.files - портреты людей для загрузки в дереве
# tree_img.html - выгрузка дерева в html формате
# tree_img.html.files/img - портреты людей в дереве
# files.tsv - соответствие исходных имен файлов в tree.ged и относительных путей в папке files (tsv)
# files - папка с картинками

def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:len(text)-len(suffix)]

def strip_begin(text, prefix):
    if not text.startswith(prefix):
        return text
    return text[len(prefix):]

def copy(src_dir, dst_dir, filenames, required=True):
    create_folder(dst_dir)
    for file in filenames:
        src_path = os.path.join(src_dir, file)
        dst_path = os.path.join(dst_dir, file)
        if not os.path.exists(src_path):
            if required:
                raise Exception('File {0} does not exists'.format(src_path))
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
                return

        if os.path.isfile(src_path):
            shutil.copy(src_path, dst_path)
        else:
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src=src_path, dst=dst_path)


def md5(fname):
    hash_md5 = hashlib.md5()
    if os.path.exists(fname):
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
    else:
        hash_md5.update(fname.encode('utf-8'))
        return hash_md5.hexdigest()

class TreeImgSvg:
    def __init__(self, img):
        self.img = img
        self.valid = True
        if img == 'tree_img.svg' or img.endswith('_tree_img.svg'):
            self.name = "" if img == 'tree_img.svg' else strip_end(img, '_tree_img.svg')
            self.files = img + '.files'
        else:
            self.valid = False

    def copy(self, src_dir, dst_dir):
        if not self.valid:
            return
        print('copy {}'.format(os.path.join(src_dir, self.img)))
        copy(src_dir, dst_dir, [self.img])
        if self.files:
            copy(src_dir, dst_dir, [self.files])


class TreeHtml:
    def __init__(self, html):
        self.html = html
        self.valid = True
        if html == 'tree_img.html' or html.endswith('_tree_img.html'):
            self.name = "" if html == "tree_img.html" else strip_end(html, '_tree_img.html')
            self.files = html + '.files'
        else:
            self.valid = False

    def copy(self, src_dir, dst_dir):
        if not self.valid:
            return
        print('copy {}'.format(os.path.join(src_dir, self.html)))
        copy(src_dir, dst_dir, [self.html])
        if self.files:
            copy(src_dir, dst_dir, [self.files])

    def create_svg_img_with_files(self, folder):
        """извлекаем svg из html и нужные картинки, конвертируем пути картинок"""
        if not self.valid:
            return None
        html_path = os.path.join(folder, self.html)
        if not os.path.isfile(html_path):
            return None

        svg = None
        with codecs.open(html_path, 'r', 'utf-8') as f:
            html = f.read()
            svg_pattern = r'(<svg[^>]*>.*?</svg>)'
            # Use DOTALL flag to match across multiple lines
            svg_match = re.search(svg_pattern, html, re.DOTALL | re.IGNORECASE)
            svg = svg_match.group(1) if svg_match else None
            # pattern stye like this
            # .s0 { fill:none;stroke:none; }
			# .s1 { font-size:12px;font-style:normal;font-weight:normal;font-family:Tahoma;fill:#000000; }
            style_pattern = r'((\s+\.s\d+\s{[^}]*})+)'
            style_match = re.search(style_pattern, html, re.DOTALL)
            style = style_match.group(1) if style_match else None

        if not svg:
            return None

        svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg
        svg = re.sub(r'(<script[^>]*>.*?</script>)', '', svg)
        svg = re.sub(r'\sxmlns:svg="(.*?)"', r' xmlns:svg="\1" xmlns="\1" xmlns:at="https://genery.com/ru"', svg)
        svg = re.sub(r'(<svg[^>]*>)',
                     r'\1\n<defs>\n\t<style type="text/css">\n\t\t<![CDATA[\n' + style + r'\n\t\t]]>\n\t</style>\n</defs>\n',
                     svg)


        svg = re.sub(r'\sdata-id="(\d+)"', r' at:id="\1"', svg)
        svg = re.sub(r'\sclass="po"\s', ' ', svg)

        tree_img_svg = TreeImgSvg(self.name + "_tree_img.svg" if self.name else "tree_img.svg")
        tree_img_svg_files = os.path.join(folder, tree_img_svg.files)
        create_folder(tree_img_svg_files, empty=True)


        matches = []

        img_pattern = r'<image[^>]*xlink:href="\./([^"]*)"[^>]*>'
        img_matches = re.finditer(img_pattern, svg)

        data_id_pattern = r'<g[^>]*at:id="(\d+)"[^>]*>'
        data_ids_matches = re.finditer(data_id_pattern, svg)

        for data_id_match in data_ids_matches:
            matches.append((data_id_match.start(), data_id_match.group(1)))

        last_group = 0
        replace_img_path = {}
        for img_match in img_matches:
            img_path = img_match.group(1)
            img_name = strip_begin(img_path, self.files + '/img/')
            while last_group + 1 < len(matches) and matches[last_group + 1][0] < img_match.start():
                last_group += 1
            person_id = matches[last_group][1]
            img_ext = os.path.splitext(img_name)[-1]
            new_img_name = 'is{}'.format(person_id) + img_ext
            new_img_path = os.path.join(tree_img_svg.files, new_img_name)
            replace_img_path[img_path] = new_img_path
            shutil.copy(src=os.path.join(folder, img_path), dst=os.path.join(folder, new_img_path))



        for old_img_path, new_img_path in replace_img_path.items():
            svg = re.sub(r'\./{}'.format(old_img_path), new_img_path, svg)

        svg_file = os.path.join(folder, tree_img_svg.img)
        with codecs.open(svg_file, 'w+', 'utf-8') as f:
            f.write(svg)

        return tree_img_svg



def select_tree_img_files(folder):
    """ДЖ5 сохраняет  *_tree_img.svg файлы и картинки к ним
       ДЖ6 можно сохранить в формате *_tree_img.html и в нем уже достать svg + картинки """
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    imgs = []
    for f in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, f)):
            img = TreeImgSvg(f)
            if img.valid:
                imgs.append(img)

            html = TreeHtml(f)
            if html.valid:
                imgs.append(html)
    return imgs


###################################################################################
##### CLIENT SIDE #################################################################
###################################################################################

def drop_tree_prefix_and_convert_uid(gedcom):
    outlines = []
    last_ind = None
    version = None
    with codecs.open(gedcom, 'r', 'utf-8') as input:
        for line in input:
            ind_match = re.search('^0 @I(\d+)@ INDI$', line)
            if ind_match is not None:
                last_ind = ind_match.group(1)

            if version is None and line.startswith('2 VERS '):
                if line.startswith('2 VERS 5'):
                    version = '5'
                elif line.startswith('2 VERS 6'):
                    version = '6'
                else:
                    version = 'other'
                print('version: {}'.format(version))


            if line.startswith('1 _UID'):
                uid = line[len('1 _UID'):].strip()
                if version == '5':
                    #  В ДЖ5 UID персоны выглядит как TREEID123_456 где TREEID123 один и тот же для всех персон
                    uid = uid.split('_', maxsplit=1)[-1]
                elif version == '6':
                    # А в ДЖ6 UID содержит символы которые опасно использовать в url (и старый _UID записан в INDI)
                    uid = last_ind
                outlines.append('1 _UID {}\n'.format(uid))
            else:
                outlines.append(line)

    with codecs.open(gedcom, 'w+', 'utf-8') as output:
        for line in outlines:
            output.write(line)


def copy_documents(gedcom, folder):
    '''
    Копируем нужные файлы с компьютера в папку folder
    Обрабатываем только файлы персон (строки вида "2 FILE D:/Some/File/path.jpg")
    '''
    create_folder(folder, empty=True)
    files = {}
    with codecs.open(gedcom, 'r', 'utf-8') as input:
        uid = None
        for line in input:
            if line.startswith('1 _UID'):
                uid = 'p' + line[len('1 _UID'):].strip()
                continue
            m = re.search('0 @F(?P<family>\d+)@ FAM', line)
            if m is not None:
                uid = 'f' + m.group('family')
                continue
            if uid is None:
                continue
            if line.startswith('2 FILE') or line.startswith('3 FILE'):
                file_path = line[len('2 FILE'):].strip()
                if file_path in files:
                    continue
                if not os.path.exists(file_path):
                    continue
                if '(private)' in file_path:
                    continue
                # копируем файл в папку folder/uid
                person_folder = os.path.join(folder, uid)
                create_folder(person_folder)
                ext = os.path.splitext(file_path)[-1]
                new_filename = md5(file_path)+ext
                new_file_path = os.path.join(person_folder, new_filename)
                shutil.copy(src=file_path, dst=new_file_path)
                files[file_path] = os.path.join(uid, new_filename)
    return files


def create_package(export_dir, archive_name):
    '''export_dir - папка с экспортированными из genery данными
       dst - имя архива
    '''
    tmp_dir = os.path.join(export_dir, 'data')
    try:
        create_folder(tmp_dir, empty=True)
        trees = select_tree_img_files(export_dir)
        print('copy trees.json')
        copy(export_dir, tmp_dir, ['trees.json'])
        print('copy tree.ged')
        copy(export_dir, tmp_dir, ['tree.ged'])
        gedcom = os.path.join(tmp_dir, 'tree.ged')
        convert_to_utf8(gedcom)
        drop_tree_prefix_and_convert_uid(gedcom)
        for tree in trees:
            tree.copy(export_dir, tmp_dir)
        files_dir = os.path.join(tmp_dir, 'files')
        print('copy documents')
        files = copy_documents(gedcom, files_dir)
        with codecs.open(os.path.join(tmp_dir, 'files.tsv'), 'w+', 'utf-8') as files_out:
            for path, copied in files.items():
                files_out.write('{0}\t{1}\n'.format(path, copied))
        print('copied {} documents'.format(len(files)))
        print('make archive')
        return shutil.make_archive(os.path.join(export_dir, archive_name), 'zip', tmp_dir)
    finally:
        shutil.rmtree(tmp_dir)

#######################################################################
#### SERVER SIDE ######################################################
#######################################################################

from gedcom import GedcomReader, GedcomWriter, Gedcom
import xml.etree.ElementTree
from datetime import date


def convert_svg(svg_file):
    '''преобразует svg файл так, чтобы ссылки на картинки вели в static/tree/preview/xxx.jpg
       у нужных блоков был бы прописан класс 'select-person' и атрибут 'person-uid'
    '''
    files_dir_name = os.path.split(svg_file)[1] + '.files'
    svg = None
    with codecs.open(svg_file, 'r', 'utf-8') as f:
        svg = f.read()
    # здесь скорее не person-uid (_UID 9c4cf28d4313fcf6b98fb3d2dfc1002a) а person-id (@I600@ INDI)
    # 0 @I600@ INDI
    # 1 _UID 9c4cf28d4313fcf6b98fb3d2dfc1002a
    svg = re.sub(r'\sat:id="(\d+)"', r' class="select-person" person-uid="\1"', svg)

    svg = svg.replace(files_dir_name, '/static/tree/files/preview')
    print('replace {} on /static/tree/files/preview'.format(files_dir_name))
    svg = re.sub('(<image[^>]+?)xlink:href=', r'\1 href="/static/1x1_white.png" lazy-href=', svg)
    with codecs.open(svg_file, 'w+', 'utf-8') as f:
        f.write(svg)


def generage_sitemap(site, trees, gedcom):
    root = xml.etree.ElementTree.Element('urlset')
    root.attrib['xmlns'] = "http://www.sitemaps.org/schemas/sitemap/0.9"

    urls = []
    for tree_name in trees:
        urls.append(site + '/' + tree_name)
    for person in gedcom.persons:
        person_uid = person.get('_UID')
        if person_uid:
            urls.append(site + '/person/' + person_uid)

    for page in urls:
        url = xml.etree.ElementTree.SubElement(root, 'url')
        loc = xml.etree.ElementTree.SubElement(url, 'loc')
        loc.text = page
        lastmod = xml.etree.ElementTree.SubElement(url, 'lastmod')
        lastmod.text = date.today().strftime('%Y-%m-%d')

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml.etree.ElementTree.tostring(root, encoding='utf-8').decode('utf-8') + '\n'

def load_tree_img(tree, src_dir, static_dir):

    if isinstance(tree, TreeHtml):
        tree = tree.create_svg_img_with_files(src_dir)
    if tree is None or not tree.valid:
        return

    print('copy {}'.format(tree.img))

    copy(src_dir, static_dir, [tree.img])
    convert_svg(os.path.join(static_dir, tree.img))
    if tree.files:
        files = list(os.listdir(os.path.join(src_dir, tree.files)))
        copy(os.path.join(src_dir, tree.files), os.path.join(static_dir, 'files', 'preview'), files)


def load_package(archive, site, static_dir, data_dir, tmp_dir):
    '''распаковывает архив базы данных
       static_dir - папка для картинок/документов
       data_dir - папка для данных
    '''
    try:
        create_folder(tmp_dir, empty=True)
        print('unpack archive')
        shutil.unpack_archive(archive, tmp_dir)

        create_folder(static_dir, empty=True)
        create_folder(data_dir, empty=True)

        # обработка gedcom файла
        print('copy tree.ged')
        gedcom = GedcomReader().read_gedcom(os.path.join(tmp_dir, 'tree.ged'))
        GedcomWriter().write_gedcom(gedcom, os.path.join(data_dir, 'tree.ged'))

        print('copy documents')
        copy(tmp_dir, data_dir, ['files.tsv'])
        print('copy trees.json')
        copy(tmp_dir, data_dir, ['trees.json'], required=False)
        print('copy files')
        copy(tmp_dir, static_dir, ['files'])

        trees = select_tree_img_files(tmp_dir)
        for tree in trees:
            load_tree_img(tree, tmp_dir, static_dir)

        with codecs.open(os.path.join(static_dir, 'sitemap.xml'), 'w', 'utf-8') as sitemap:
            sitemap.write(generage_sitemap(site, [tree.name for tree in trees], gedcom))

    finally:
        pass
        # shutil.rmtree(tmp_dir)




