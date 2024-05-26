# genotree

You can see working beta at http://me-in-history.ru

## How to start:
The site has following structure

me_in_history
|
├── config
│   ├── app.secret.txt
│   ├── oauth.config // data to connect to vk, fb or odnoklassniki
│   └── site.config // config of pathes on your site
├── genotree  // github content
│   ├── README.md
│   └── src
│       ├── app.py
│       ├── .... source code files
│       └── wsgi.py
├── static // static data for site generated when you update tree data
│   ├── content
│   │   └── sources.html
│   └── tree
│       ├── cherepanovy_tree_img.svg
│       ├── farenuyk_tree_img.svg
│       ├── files
│       │   └── ... photos, biographies, texts, documents
│       ├── motyrevy_tree_img.svg
│       ├── sitemap.xml
│       ├── tree_img.svg
│       └── zhagoriny_tree_img.svg
├── data // data bases and your tree data (not public static content)
│   ├── db
│   │   └── tree.db
│   └── tree
│       ├── files.tsv
│       └── tree.ged
├── tmp
└── upload
    ├── data.zip // uploaded new version of tree data
    └── tmp_dir
 
