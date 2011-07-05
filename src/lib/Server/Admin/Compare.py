import lxml.etree
import os

import Bcfg2.Server.Admin


class Compare(Bcfg2.Server.Admin.Mode):
    __shorthelp__ = ("Determine differences between files or "
                     "directories of client specification instances")
    __longhelp__ = (__shorthelp__ + "\n\nbcfg2-admin compare <file1> <file2>"
                                    "\nbcfg2-admin compare -r <dir1> <dir2>")
    __usage__ = ("bcfg2-admin compare <old> <new>\n\n"
                 "     -r\trecursive")

    def __init__(self, configfile):
        Bcfg2.Server.Admin.Mode.__init__(self, configfile)
        self.important = {'Path': ['name', 'type', 'owner', 'group', 'perms',
                                   'important', 'paranoid', 'sensitive',
                                   'dev_type', 'major', 'minor', 'prune',
                                   'encoding', 'empty', 'to', 'recursive',
                                   'vcstype', 'sourceurl', 'revision'],
                          'Package': ['name', 'type', 'version', 'simplefile',
                                      'verify'],
                          'Service': ['name', 'type', 'status', 'mode',
                                      'target', 'sequence', 'parameters'],
                          'Action': ['name', 'timing', 'when', 'status',
                                     'command'],
                          'PostInstall': ['name']
                          }

    def compareStructures(self, new, old):
        if new.tag == 'Independent':
            bundle = 'Base'
        else:
            bundle = new.get('name')

        identical = True

        for child in new.getchildren():
            if child.tag not in self.important:
                print("Tag type %s not handled" % (child.tag))
                continue
            equiv = old.xpath('%s[@name="%s"]' %
                              (child.tag, child.get('name')))
            if len(equiv) == 0:
                print(" %s %s in bundle %s:\n  only in new configuration" %
                      (child.tag, child.get('name'), bundle))
                identical = False
                continue
            diff = []
            if child.tag == 'Path' and child.get('type') == 'file' and \
               child.text != equiv[0].text:
                diff.append('contents')
            attrdiff = [field for field in self.important[child.tag] if \
                        child.get(field) != equiv[0].get(field)]
            if attrdiff:
                diff.append('attributes (%s)' % ', '.join(attrdiff))
            if diff:
                print(" %s %s in bundle %s:\n  %s differ" % (child.tag, \
                      child.get('name'), bundle, ' and '.join(diff)))
                identical = False

        for child in old.getchildren():
            if child.tag not in self.important:
                print("Tag type %s not handled" % (child.tag))
            elif len(new.xpath('%s[@name="%s"]' %
                     (child.tag, child.get('name')))) == 0:
                print(" %s %s in bundle %s:\n  only in old configuration" %
                      (child.tag, child.get('name'), bundle))
                identical = False

        return identical

    def compareSpecifications(self, path1, path2):
        try:
            new = lxml.etree.parse(path1).getroot()
        except IOError:
            print("Failed to read %s" % (path1))
            raise SystemExit(1)

        try:
            old = lxml.etree.parse(path2).getroot()
        except IOError:
            print("Failed to read %s" % (path2))
            raise SystemExit(1)

        for src in [new, old]:
            for bundle in src.findall('./Bundle'):
                if bundle.get('name')[-4:] == '.xml':
                    bundle.set('name', bundle.get('name')[:-4])

        rcs = []
        for bundle in new.findall('./Bundle'):
            equiv = old.xpath('Bundle[@name="%s"]' % (bundle.get('name')))
            if len(equiv) == 0:
                print("couldnt find matching bundle for %s" % bundle.get('name'))
                continue
            if len(equiv) == 1:
                if self.compareStructures(bundle, equiv[0]):
                    new.remove(bundle)
                    old.remove(equiv[0])
                    rcs.append(True)
                else:
                    rcs.append(False)
            else:
                print("Unmatched bundle %s" % (bundle.get('name')))
                rcs.append(False)
        i1 = new.find('./Independent')
        i2 = old.find('./Independent')
        if self.compareStructures(i1, i2):
            new.remove(i1)
            old.remove(i2)
        else:
            rcs.append(False)
        return False not in rcs

    def __call__(self, args):
        Bcfg2.Server.Admin.Mode.__call__(self, args)
        if len(args) == 0:
            self.errExit("No argument specified.\n"
                         "Please see bcfg2-admin compare help for usage.")
        if '-r' in args:
            args = list(args)
            args.remove('-r')
            (oldd, newd) = args
            (old, new) = [os.listdir(spot) for spot in args]
            for item in old:
                print("Entry:", item)
                state = self.__call__([oldd + '/' + item, newd + '/' + item])
                new.remove(item)
                if state:
                    print("Entry:", item, "good")
                else:
                    print("Entry:", item, "bad")
            if new:
                print("new has extra entries", new)
            return
        try:
            (old, new) = args
            return self.compareSpecifications(new, old)
        except IndexError:
            print(self.__call__.__doc__)
            raise SystemExit(1)
