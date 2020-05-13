#!/usr/bin/python

import sys
import MySQLdb

db = MySQLdb.connect(host='localhost', user='ebender',
                     passwd='tr33house', db='MatrixTDB')

cursor = db.cursor()


# Main

cursor.execute('SELECT DISTINCT ffg_fltr_id FROM %s' % (sys.argv[1]))
ids = []
for id in cursor.fetchall():
    ids.append(id[0])
for i in ids:
    cursor.execute('SELECT ffg_grp_id FROM %s WHERE ffg_fltr_id = %s' %
                   (sys.argv[1], i))
    res = cursor.fetchall()
    print(str(i) + ': ', end=' ')
    for r in res:
        print(str(r[0]) + ',', end=' ')
    print()
