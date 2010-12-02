#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''W3C SRGS parser

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import sys, os, re, codecs
from lxml import etree
from hiragana2phoneme import hiragana2phoneme

def isempty(node):
    if node.nodeName == '#text':
        if node.data.strip('\n ') == '':
            return True
    return False

class PLS:
    """ Utility class to parse W3C Pronunciation Lexicon Specification."""

    def __init__(self):
        self._dict = {}

    def parse(self, files):
        grapheme = []
        phoneme = []
        try:
            for f in files:
                for event, elem in etree.iterparse(f):
                    if elem.tag.find("lexeme") >= 0:
                        for g in grapheme:
                            for p in phoneme:
                                try:
                                    self._dict[g].append(p)
                                except KeyError:
                                    self._dict[g] = [p,]
                        grapheme = []
                        phoneme = []
                    if elem.tag.find("grapheme") >= 0:
                        grapheme.append(elem.text)
                    if elem.tag.find("phoneme") >= 0:
                        phoneme.append(elem.text)
        except etree.XMLSyntaxError, e:
            print "[error] invalid xml syntax"
            print e
        except IOError, e:
            print "[error] IO error: unable to open file ", file
            print e
        return self

class SRGSItem:
    def __init__(self):
        self._type = None
        self._items = None

    def parse(self, node):
        self._type = node.tag.replace('{http://www.w3.org/2001/06/grammar}', '')
        if self._type == "item":
            self._repeatmin = None
            self._repeatmax = None
            try:
                repeat = node.attrib['repeat']
                if repeat:
                    rp = repeat.split('-')
                    if rp[0]:
                        self._repeatmin = int(rp[0])
                    if rp[1]:
                        self._repeatmax = int(rp[1])
            except KeyError:
                pass
            children = node.getchildren()
            if len(children) > 0:
                self._items = [SRGSItem().parse(c) for c in node.getchildren() if type(c) is not etree._Comment]
            else:
                textnode = SRGSItem()
                textnode._type = "#text"
                textnode._words = [w for w in re.split(u"( |[\\\"'].*[\\\"'])", node.text) if w != '' and w != u' ']
                self._items = [textnode,]
        elif self._type == "one-of":
            self._items = [SRGSItem().parse(c) for c in node.getchildren() if type(c) is not etree._Comment]
        elif self._type == "ruleref":
            self._uri = node.get('uri')
        elif self._type == "tag":
            self._tag = node.text
        return self

class SRGSRule:
    def __init__(self):
        self._id = None
        self._items = []

    def parse(self, node):
        self._id = node.get('id')
        self._items = [SRGSItem().parse(c) for c in node.getchildren() if type(c) is not etree._Comment]
        return self

class SRGS:
    """ Utility class to parse W3C Speech Recognition Grammar Specification."""

    def __init__(self, file):
        self._filename = file
        self._rules = {}
        self._lang = "en"
        self._rootrule = None
        self._lex = None
        self._node = None
        try:
            doc = etree.parse(file)
            doc.xinclude()
            self._node = doc.getroot()
        except etree.XMLSyntaxError, e:
            print "[error] invalid xml syntax"
            print e
        except IOError, e:
            print "[error] IO error: unable to open file ", file
            print e
        self.parse(self._node)

    def parse(self, node):
        self._lang = node.get("{http://www.w3.org/XML/1998/namespace}lang")
        lexnode = node.findall("{%s}lexicon" % (node.nsmap[None],))
        if lexnode is not None:
            self._lex = [os.path.join(os.path.dirname(self._filename), l.get('uri')) for l in lexnode]
        for r in node.findall("{%s}rule" % (node.nsmap[None],)):
            rr = SRGSRule().parse(r)
            self._rules[rr._id] = rr
        self._rootrule = node.get('root')

    def wordlist_recur(self, item, words):
        if item._type == "#text":
            words.extend(item._words)
        elif item._type == "item":
            for i in item._items:
                self.wordlist_recur(i, words)
        elif item._type == "one-of":
            for i in item._items:
                self.wordlist_recur(i, words)
        elif item._type == "ruleref":
            pass
        elif item._type == "tag":
            pass

    def wordlist(self):
        words = []
        for r in self._rules.values():
            for i in r._items:
                self.wordlist_recur(i, words)
        return words

    def toJulius_recur(self, item, dfa, startstate, endstate):
        if item._type == "#text":
            currentstate = startstate
            for w in item._words[:-1]:
                newstate = dfa.newstate()
                dfa.append((currentstate, w, newstate))
                currentstate = newstate
            dfa.append((currentstate, item._words[-1], endstate))
        elif item._type == "item":
            if item._repeatmax:
                currentstate = startstate
                if item._repeatmax == 1:
                    for i in item._items[:-1]:
                        newstate = dfa.newstate()
                        self.toJulius_recur(i, dfa, currentstate, newstate)
                        currentstate = newstate
                    self.toJulius_recur(item._items[-1], dfa, currentstate, endstate)
                else:
                    for l in range(0, item._repeatmax - 1):
                        newstate = dfa.newstate()
                        currentstate2 = currentstate
                        for i in item._items[:-1]:
                            newstate2 = dfa.newstate()
                            self.toJulius_recur(i, dfa, currentstate2, newstate2)
                            currentstate2 = newstate2
                        self.toJulius_recur(item._items[-1], dfa, currentstate, newstate)
                        for v in dfa._dfa:
                            if v[2] == currentstate:
                                dfa.append((v[0], v[1], endstate))
                        currentstate = newstate
                    currentstate2 = currentstate
                    for i in item._items[:-1]:
                        newstate2 = dfa.newstate()
                        self.toJulius_recur(i, dfa, currentstate2, newstate2)
                        currentstate2 = newstate2
                    self.toJulius_recur(item._items[-1], dfa, currentstate, endstate)
                    for v in dfa._dfa:
                        if v[2] == currentstate:
                            dfa.append((v[0], v[1], endstate))
            else:
                currentstate = startstate
                for i in item._items[:-1]:
                    newstate = dfa.newstate()
                    self.toJulius_recur(i, dfa, currentstate, newstate)
                    currentstate = newstate
                self.toJulius_recur(item._items[-1], dfa, currentstate, endstate)
            if item._repeatmin == 0: # add skip transition
                for v in dfa._dfa:
                    if v[2] == startstate:
                        dfa.append((v[0], v[1], endstate))
        elif item._type == "one-of":
            for i in item._items:
                self.toJulius_recur(i, dfa, startstate, endstate)
        elif item._type == "ruleref":
            if item._uri[0] != '#':
                print "[error] reference to external uri: %s" % (item._uri,)
                return
            try:
                root = self._rules[item._uri[1:]]
            except KeyError:
                print "[error] unknown rule: %s" % (item._uri,)
                return
            currentstate = startstate
            for i in root._items[:-1]:
                newstate = dfa.newstate()
                self.toJulius_recur(i, dfa, currentstate, newstate)
                currentstate = newstate
            self.toJulius_recur(root._items[-1], dfa, currentstate, endstate)
        elif item._type == "tag":
            pass
    
    def toJulius(self, rootrule = None):

        if rootrule is None:
            root = self._rules[self._rootrule]
        else:
            root = self._rules[rootrule]

        if self._lex is None:
            print "[error] <lexicon uri=...> node is required in the grammar file."
            return None
        lex = PLS().parse(self._lex)

        dfa = DFA()
        startstate = dfa.newstate()
        dfa.append((dfa.STARTSTATE, '<s>', startstate))
        dfa.append((dfa.ENDSTATE, '</s>', dfa.EOA))
        currentstate = startstate
        for i in root._items[:-1]:
            newstate = dfa.newstate()
            self.toJulius_recur(i, dfa, currentstate, newstate)
            currentstate = newstate
        self.toJulius_recur(root._items[-1], dfa, currentstate, dfa.ENDSTATE)
        revdfa = dfa.reverse()

        dict = {}
        if self._lang == 'jp':
            dict['<s>'] = ('silB',)
            dict['</s>'] = ('silE',)
        else:
            dict['<s>'] = ('sil',)
            dict['</s>'] = ('sil',)
            #dict['<sp>'] = ('sp',)
        for v in revdfa:
            if v[1] != -1:
                try:
                    if dict.has_key(v[1]) == False:
                        dict[v[1]] = lex._dict[v[1]]
                except KeyError:
                    print "[error] undefined lexicon: %s" % (v[1],)
                    return ""
        dict2id = {}
        for k in dict.keys():
            dict2id[k] = len(dict2id)

        jdfa = list()
        for v in revdfa:
            if v[1] == -1:
                jdfa.append((v[0], v[1], v[2], 1, 0))
                continue
            wid = dict2id[v[1]]
            jdfa.append((v[0], wid, v[2], 0, 0))
        jdfa.sort(lambda x, y: x[0] - y[0])

        phonedict = list()
        h2p =  hiragana2phoneme()
        for k in dict.keys():
            for p in dict[k]:
                if p[:2] == '{{':
                    (ptype, pval) = p.strip('{}').split('|')
                    if ptype.upper() in ('KANA', 'X-KANA'):
                        phonedict.append((dict2id[k], k, h2p.convert(pval)))
                    else:
                        phonedict.append((dict2id[k], k, pval))
                else:
                    phonedict.append((dict2id[k], k, p))
        phonedict.sort(lambda x, y: x[0] - y[0])

        str = u""
        for d in jdfa:
            str += u"%i %i %i %i %i\n" % d
        str += u"DFAEND\n"
        for p in phonedict:
            str += u"%i\t[%s]\t%s\n" % p
        str += u"DICEND\n"

        return str

class DFA:
    """ Utility class to manage DFA """

    STARTSTATE = 0
    ENDSTATE = 1
    EOA = -1 # End Of Automaton
    
    def __init__(self):
        self._dfa = list()
        self._totalstate = 2

    def newstate(self):
        self._totalstate += 1
        return self._totalstate - 1
    
    def append(self, value):
        self._dfa.append(value)
        
    def reverse(self): # convert dfa into reverse order
        newdfa = list()
        for v in self._dfa:
            fromstate = v[0]
            tostate = v[2]
            if tostate == self.EOA:
                tostate = self.STARTSTATE
            elif fromstate == self.STARTSTATE:
                newdfa.append((tostate, v[1], self._totalstate))
                newdfa.append((self._totalstate, -1, -1))
                continue
            newdfa.append((tostate, v[1], fromstate))
        return newdfa

def _test():
    import doctest
    doctest.testmod()
    #import profile
    #profile.run('main()')

if __name__ == "__main__":
    _test()