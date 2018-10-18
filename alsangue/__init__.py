#!/usr/bin/env python3

#    alsangue
#
#    ----------------------------------------------------------------------
#    Copyright © 2018  Pellegrino Prevete
#
#    All rights reserved
#    ----------------------------------------------------------------------
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#


from argparse import ArgumentParser
from ast import literal_eval
from bs4 import BeautifulSoup
from copy import copy
from os import listdir, mkdir, getcwd
from os import chdir as cd
from os import symlink as ln
from os import remove as rm
from os.path import realpath, dirname, relpath, getmtime
from re import sub
from setproctitle import setproctitle
from shutil import copyfile as cp
from time import strftime, strptime, localtime
import locale

name = "alsangue"

setproctitle(name)

hidden = lambda f : f.startswith('.')

def ls(dir):
    """Returns non hidden files in a dir

    Args:
        dir (str): path of the dir to be read
    """
    files = listdir(dir)
    return [f for f in files if not hidden(f)]

def date_print(date):
    """Converts ISO 8601 calendar date (YYYY-MM-DD) in a fancy format
    
    Args:
        date (str): YYYY-MM-DD
    Returns:
        The date converted (i.e. 26 August 2018)
    """
    date = strptime(date, "%Y/%M/%d")
    return strftime('%d %B %Y', date)

def getlastedit(f,sitemap=False):
    """Return the date of the last edit of a file
    
    Args:
        f (str): path of the file
    Returns:
        The date in the fancy format (i.e. 26 August 2018)
    """
    epoch = getmtime(f)
    date = localtime(epoch)
    if sitemap:
        return strftime('%Y-%m-%d', date)
    return strftime('%d %B %Y', date)

def dict_from_file(f):
    """Load a Python dictionary read from a file into a variable

    Args:
        f (str): path of the file containing the dictionary
    Returns:
        content (dict): the dictionary read from the file
    """
    with open(f, 'r') as g:
        content = literal_eval(g.read())
        g.close()
    return content

def load(f):
    """Load a text file into a variable
    
    Args:
        f (str): path of the text file
    Returns:
        content (str): the variable containing the text
    """
    with open(f) as g:
        content = g.read()
        g.close()
    return content

def save(soup, file):
    """Save a soup object in file

    Args:
        soup: instance of BeautifulSoup object
        file (str): path of the file
    """
    with open(file, "w") as f:
        f.write(str(soup))
        f.close()

class Sitemap:
    def __init__(self, path):
        code = """<?xml version="1.0" encoding="UTF-8"?><urlset xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset> """
        self.path = path
        self.soup = BeautifulSoup(code, 'xml')
        self.urlset = self.soup.find('urlset')

    def add_url(self, loc, lastmod=None, locales={}, changefreq='monthly', priority='0.5'):
        soup = BeautifulSoup('', 'lxml')
        url = soup.new_tag('url')
        self.urlset.append(url)

        loc_tag = soup.new_tag('loc')
        loc_tag.append(loc)
        url.append(loc_tag)

        if lastmod != None:
            lastmod_tag = soup.new_tag('lastmod')
            lastmod_tag.append(lastmod)
            url.append(lastmod_tag)

        for code in locales.keys():
            url.append(BeautifulSoup("", 'xml').new_tag('xhtml:link', attrs={'rel':'alternate', 'hreflang':code, 'href':locales[code]}))

        changefreq_tag = soup.new_tag('changefreq')
        changefreq_tag.append(changefreq)
        url.append(changefreq_tag)

        priority_tag = soup.new_tag('priority')
        priority_tag.append(priority)
        url.append(priority_tag)

    def save(self):
        save(self.soup.prettify(), self.path + "/sitemap.xml")        

class Builder:
    """Builds the website
    
    The builder will scan for "article" files (Python dictionaries with predefined fields)
    in the "articles" directory and "author" files in "authors" directory.
    Different language builds of the website will be builded if the writer has written
    articles or sections in his author file in a language present in the "locales" directory.

    Args:
        content_path (str): path of content directory;
        build_path (str): path where the built files have to reside;
    """
    alsangue_path = dirname(realpath(__file__))

    def __init__(self, content_path=alsangue_path, build_path=alsangue_path + "/build"):

        alsangue_path = dirname(realpath(__file__))

        self.build_path = realpath(build_path)
        self.content_path = realpath(content_path)

        self.config = dict_from_file(content_path + "/config")

        locales = [realpath(alsangue_path + "/locales/" + l) for l in ls(alsangue_path + "/locales")]
        self.locales = [dict_from_file(l) for l in locales]
        for l in self.locales:
            if l["ISO/IEC 15897"] != self.config["locale"]:
                code = copy(l['code'])
                l['build path'] = lambda x: "/" + code + x
            else:
                l['build path'] = lambda x: "/" + x[1:]
        self.build_tree()

        self.sitemap = Sitemap(build_path)

        self.templates_path = content_path + "/templates"
      
        self.articles = [realpath(content_path + "/articles/" + a) for a in ls(content_path + "/articles")]
        self.authors = [realpath(content_path + "/authors/" + a) for a in ls(content_path + "/authors")]
 
        for a in self.articles:
            self.build_article(a)
        for a in self.authors:
            self.build_author_page(a)
            self.build_archive(a)

        for l in self.locales:
            try:
                ln(self.build_path + l['build path'](self.config['homepage'] + ".html"), self.build_path + l['build path']("/index.html"))
            except FileExistsError as e:
                rm(self.build_path + l['build path']("/index.html"))
                ln(self.build_path + l['build path'](self.config['homepage'] + ".html"), self.build_path + l['build path']("/index.html")) 

        self.sitemap.save()

    def build_tree(self):
        """Create directories structure in build directory
        
        The structure is pretty much 'build/content_type/content_name' for the
        main language and 'build/language_code/content_type/content_name' for the others.
        """
        types = ["articles", "authors", "archive"]

        try:
            mkdir(self.build_path)
        except FileExistsError as e:
            pass
        try:
            mkdir(self.build_path + "/res")
        except FileExistsError as e:
            pass
        for f in ls(self.content_path + "/res"):
            cp(self.content_path + "/res/" + f, self.build_path + "/res/" + f)

        for l in self.locales:
            try:
                mkdir(self.build_path + l['build path']("/"))
            except FileExistsError as e:
                pass
            for t in types:
                try:
                    mkdir(self.build_path + l['build path']("/" + t))
                except FileExistsError as e:
                    pass

    def build_article(self, article): 
        """Build an html page for an article

        For any language present in the "locales" directory the function will check if the
        article is translated in that particular locale and publish a page for that language.

        The articles will be created using the "article.html" template in the homonym directory.

        Args:
            article (str): path of the article file. See example directory to know how to populate it.
        """
        document = dict_from_file(article)
        locales = [loc for loc in self.locales if loc["ISO/IEC 15897"] in document.keys()]

        article_name = article.split("/")[-1]
        article_page = "/articles/" + article_name + ".html"
        article_path = {}
        loc = {}
        for l in locales:
            article_path[l["code"]] = self.config['domain'] + l["build path"](article_page)

        template = load(self.templates_path + "/article.html")

        for l in locales:
            soup = BeautifulSoup(template, 'lxml')
            locale.setlocale(locale.LC_ALL, l["ISO/IEC 15897"])
            html_tag = soup.find(id="html")
            html_tag.attrs["lang"] = l["code"]

            head = soup.find(id="head")
            title = soup.new_tag("title")
            title.append(document[l["ISO/IEC 15897"]]["title"])
            head.append(title)
 
            author = soup.find(id="author")
            author.string = document["author"]

            for a in self.authors:
                if dict_from_file(a)['author'] == document['author']:
                    author_path = self.config['domain'] + l['build path']("/authors/" + a.split("/")[-1] + ".html")

            author.attrs["href"] = author_path 

            title = soup.find(id="title")
            title.string = document[l["ISO/IEC 15897"]]["title"]

            content = soup.find(id="content")
            content_soup = BeautifulSoup(document[l["ISO/IEC 15897"]]['content'], 'html.parser')
            content.append(content_soup)

            if "date" in document.keys():
                date = soup.find(id="date")
                date.string = l["created"] + date_print(document["date"])

            lastedit = soup.find(id="last-edit")
            lastedit.string = l["last-edit"] + getlastedit(article) 
 
            locales_tag = soup.find(id="locales")
            for m in locales:
                if m == l:
                    locales_content = "[" + m["code"] + "]"
                    locales_tag.append(locales_content)
                else:
                    locale_tag = soup.new_tag("a", attrs={"href":article_path[m['code']]})
                    locale_tag.append(m["code"])
                    locales_tag.append("[")
                    locales_tag.append(locale_tag)
                    locales_tag.append("]")
    
            license_tag = soup.find(id="license")
            license_soup = BeautifulSoup(l[self.config["license"]], 'html.parser')
            license_tag.append(license_soup)

            article_sitemap = copy(article_path[l['code']])
            self.sitemap.add_url(article_sitemap, getlastedit(article, sitemap=True), locales=article_path, changefreq='monthly', priority='0.8')

            save(soup, self.build_path + l['build path'](article_page))

    def select_articles(self, locale, sort="last_edit_recent_to_old", author=None):
        """Select articles according to different criteria.

        Args:
            locale (str): language as an (ISO/IEC 15897 string) of the articles to be returned
            sort (str): values can be:
                - last_edit_recent_to_old: articles are appended in the list from the last to the oldest edited one
            author (str): name of the author
        Returns:
            (list) paths of selected articles
        """
        articles = [a for a in self.articles if locale in dict_from_file(a).keys()]
        if sort == "last_edit_recent_to_old":
            sorted_indexes = sorted(range(len(articles)), key=lambda k: getmtime(articles[k]), reverse=True)
            articles = [articles[i] for i in sorted_indexes]
        if author != None:
            author_articles = [a for a in articles if dict_from_file(a)["author"] == author]
            return author_articles
        return articles

    def build_author_page(self, author):
        """Builds personal page of the author.

        Args:
            author (str): path of the author file. It has to be a Python dictionary
                having the following keys:
                - author (str): name of the author
                - email (str): email of the author (optional)
                - pgp (str): pgp pub key of the author (optional)
                - xmpp (str): xmpp address of the author (optional)
                - doge (str): doge address of the author (optional)
                - btc (str): btc address of the author (optional)
                - sections (list): each section must be a dictionary having locale
                  as key; each locale is a dictionary with keys "title" and "content",
                  the latter being html code.
                For an example, check the omonymous directory;
        Note:
            Produces an html page in {/language_code/}authors/
        """
        document = dict_from_file(author)

        author_name = author.split("/")[-1]
        author_page = "/authors/" + author_name + ".html"
        archive_page = "/archive/" + author_name + ".html"
        author_path = {}
        archive_path = {}
        for l in self.locales:
            author_path[l["code"]] = self.config['domain'] + l['build path'](author_page)
            archive_path[l["code"]] = self.config['domain'] + l['build path'](archive_page)

        template = load(self.templates_path + "/author.html")

        for l in self.locales:
            soup = BeautifulSoup(template, 'lxml')

            html_tag = soup.find(id="html")
            html_tag.attrs["lang"] = l["code"]

            head_tag = soup.find(id="head")
            page_title = soup.new_tag("title")
            page_title.append(document["author"])
            head_tag.append(page_title)

            author_tag = soup.find(id="author")
            author_tag.string = document["author"]

            sections = soup.find(id="sections")

            articles = soup.new_tag("div", id="last-articles")
            sections.append(articles)
            title = soup.new_tag("h2")
            title.append(l["articles"])
            articles.append(title)
            ul = soup.new_tag("ul")

            showcase_articles = self.select_articles(l["ISO/IEC 15897"], author=document['author'])
 
            for a in showcase_articles[0:5]:
                article = dict_from_file(a)
                
                article_path = self.config['domain'] + l['build path']("/articles/" + a.split("/")[-1] + ".html")
                li = soup.new_tag("li")
                a = soup.new_tag("a", attrs={"href":article_path})
                a.append(article[l["ISO/IEC 15897"]]["title"])
                li.append(a)
                ul.append(li)

            if len(showcase_articles) > 5:
                more_articles_soup = soup.new_tag("a", id="archive", attrs={"class":"archive", "href":archive_path})
                more_articles_soup.append(l["archive"])
                ul.append(more_articles_soup)
            articles.append(ul)

            doc_sections = [s for s in document["sections"] if l["ISO/IEC 15897"] in s.keys()]

            for s in doc_sections:
                section = soup.new_tag("div", id=sub(" ", "_", s[l["ISO/IEC 15897"]]["title"]))
                title = soup.new_tag("h2")
                title.append(s[l["ISO/IEC 15897"]]["title"])
                content = soup.new_tag("div")
                content_soup = BeautifulSoup(s[l["ISO/IEC 15897"]]["content"], "html.parser")
                content.append(content_soup)
                section.append(title)
                section.append(content)
                sections.append(section)

            contacts = soup.find(id="contacts")
            title = soup.new_tag("h2")
            title.append(l["contacts"])
            contacts.append(title)
            contact_types = soup.new_tag("ul", id="contact_types")

            if 'xmpp' in document.keys():
                xmpp = soup.new_tag("li", id="xmpp")
                xmpp_link = soup.new_tag("a", id="xmpp_link", attrs={"href":"xmpp:"+document["xmpp"]})
                xmpp_link.append(document['xmpp'])
                xmpp.append("XMPP: ")
                xmpp.append(xmpp_link)
                contact_types.append(xmpp)

            if 'email' in document.keys():
                email = soup.new_tag("li", id="email")
                email_link = soup.new_tag("a", id="email_link", attrs={"href":"mailto:"+document["email"]})
                email_link.append(document["email"])
                email.append("Email: ")
                email.append(email_link)
                contact_types.append(email)

            if 'pgp' in document.keys():
                pgp = soup.new_tag("li", id="pgp")
                pgp.append("PGP: ")
                pgp_fingerprint = soup.new_tag("span", attrs={"class":"hash"})
                pgp_fingerprint.string = document["pgp"]
                pgp.append(pgp_fingerprint)
                contact_types.append(pgp)

            if 'doge' in document.keys():
                doge = soup.new_tag("li", id="doge")
                doge.append("DOGE: ")
                doge_address = soup.new_tag("span", attrs={"class":"hash"})
                doge_address.string = document["doge"]
                doge.append(doge_address)
                contact_types.append(doge)

            if 'btc' in document.keys():
                btc = soup.new_tag("li", id="btc")
                btc.append("BTC: ")
                btc_address = soup.new_tag("span", attrs={"class":"hash"})
                btc_address.string = document["btc"]
                btc.append(btc_address)
                contact_types.append(btc)

            contacts.append(contact_types)
            sections.append(contacts)       
            
            locales_tag = soup.find(id="locales")
            for m in self.locales:
                if m == l:
                    locales_content = "[" + m["code"] + "]"
                    locales_tag.append(locales_content)
                else:
                    locale_tag = soup.new_tag("a", attrs={"href":author_path[m["code"]]})
                    locale_tag.append(m["code"])
                    locales_tag.append("[")
                    locales_tag.append(locale_tag)
                    locales_tag.append("]")
           
            license_tag = soup.find(id="license")
            license_soup = BeautifulSoup(l[self.config["license"]], 'html.parser')
            license_tag.append(license_soup)

            self.sitemap.add_url(author_path[l['code']], getlastedit(author, sitemap=True), locales=author_path, changefreq='monthly', priority='1')

            save(soup, self.build_path + l['build path'](author_page))

    def build_archive(self, author):
        """Builds an archive page containing authors article

        Args:
            author (str): path of the author file
        Note:
            Produces an html page in {/language_code/}archive/author
        """
        document = dict_from_file(author)

        locales = []
        for l in self.locales:
            l['articles'] = self.select_articles(l["ISO/IEC 15897"], author=document['author'])
            if l['articles'] != []:
               locales.append(l)

        author_name = author.split("/")[-1]
        author_page = "/authors/" + author_name + ".html"
        author_path = {}
        for l in locales:
            author_path[l['code']] = self.config['domain'] + l['build path'](author_page)

        template = load(self.templates_path + "/archive.html")

        archive_page = "/archive/" + author_name + ".html"
        archive_path = {}
        for l in locales:
            archive_path[l['code']] = self.config['domain'] + l['build path'](archive_page)


        for l in locales:

            soup = BeautifulSoup(template, "lxml")

            html_tag = soup.find(id="html")
            html_tag.attrs["lang"] = l["code"]
            head = soup.find(id="head")
            page_title = soup.new_tag("title")
            page_title.append(l["archive head"] + document["author"])
            head.append(page_title)
      
            author_head = soup.find(id="author")
            author_head.string = document["author"]
            author_head.attrs["href"] = author_path[l['code']]
 
            title = soup.find(id="title")
            title.string = l["archive"]
            body = soup.find(id="body")
            ul = soup.new_tag("ul", id="articles")

            for a in l['articles']:
                article = dict_from_file(a)
                a = a.split("/")[-1]
                if l["ISO/IEC 15897"] in article.keys():
                    url = self.config['domain'] + l['build path']("/articles/" + a + ".html")
                    article_tag = soup.new_tag("a", attrs={"href":url})
                    article_tag.append(article[l["ISO/IEC 15897"]]["title"])
                    li = soup.new_tag("li")
                    li.append(article_tag)
                    ul.append(li)
            body.append(ul)

            locales_tag = soup.find(id="locales")
            for m in self.locales:
                if m == l:
                    locales_content = "[" + m["code"] + "]"
                    locales_tag.append(locales_content)
                else:
                    locale_tag = soup.new_tag("a", attrs={"href":archive_path[m["code"]]})
                    locale_tag.append(m["code"])
                    locales_tag.append("[")
                    locales_tag.append(locale_tag)
                    locales_tag.append("]")

            license_tag = soup.find(id="license")
            license_soup = BeautifulSoup(l[self.config["license"]], 'html.parser')
            license_tag.append(license_soup)

            self.sitemap.add_url(archive_path[l['code']], getlastedit(author, sitemap=True), locales=archive_path, changefreq='monthly', priority='0.5')

            save(soup, self.build_path + l['build path']("/archive/" + author_name + ".html")) 

def main():
    parser = ArgumentParser(description="builds statics websites")
    parser.add_argument("content_directory", nargs='?', default=getcwd() + "/content", help="directory of the website structure; default: ./content")
    parser.add_argument("build_directory", nargs='?', default=getcwd() + "/build", help="where to create 'build' directory; default: ./build")
    parser.add_argument("--verbose", dest="verbose", action="store_true", default=False, help="extended output")

    args = parser.parse_args()
    if args.verbose:
        print(args)
        print(args.content_directory)
        print(args.build_directory)
    build = Builder(content_path=args.content_directory, build_path=args.build_directory)
            

#builder = Builder()
