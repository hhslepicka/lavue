#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2017 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
#

""" Provides pni file writer """

import math
import os
import sys
import numpy as np
from pninexus import h5cpp

from . import filewriter
# from .Types import nptype


def nptype(dtype):
    """ converts to numpy types

    :param dtype: h5 writer type type
    :type dtype: :obj:`str`
    :returns: nupy type
    :rtype: :obj:`str`
    """
    if str(dtype) in ['string', b'string']:
        return 'str'
    return dtype


if sys.version_info > (3,):
    unicode = str
    long = int
else:
    bytes = str


def _tostr(text):
    """ converts text  to str type

    :param text: text
    :type text: :obj:`bytes` or :obj:`unicode`
    :returns: text in str type
    :rtype: :obj:`str`
    """
    if isinstance(text, str):
        return text
    elif sys.version_info > (3,):
        return str(text, "utf8")
    else:
        return str(text)


def _slice2selection(t, shape):
    """ converts slice(s) to selection

    :param t: slice tuple
    :type t: :obj:`tuple`
    :return shape: field shape
    :type shape: :obj:`list` < :obj:`int` >
    :returns: hyperslab selection
    :rtype: :class:`h5cpp.dataspace.Hyperslab`
    """
    if t is Ellipsis:
        return None
    elif isinstance(t, slice):
        start = t.start or 0
        stop = t.stop or shape[0]
        if start < 0:
            start == shape[0] + start
        if stop < 0:
            stop == shape[0] + stop
        if t.step in [None, 1]:
            return h5cpp.dataspace.Hyperslab(
                offset=(start,), block=((stop - start),))
        else:
            return h5cpp.dataspace.Hyperslab(
                offset=(start,),
                count=int(math.ceil((stop - start) / float(t.step))),
                stride=(t.step - 1,))
    elif isinstance(t, (int, long)):
        return h5cpp.dataspace.Hyperslab(
            offset=(t,), block=(1,))
    elif isinstance(t, (list, tuple)):
        offset = []
        block = []
        count = []
        stride = []
        it = -1
        for tit, tel in enumerate(t):
            it += 1
            if isinstance(tel, (int, long)):
                if tel < 0:
                    offset.append(shape[it] + tel)
                else:
                    offset.append(tel)
                block.append(1)
                count.append(1)
                stride.append(1)
            elif isinstance(tel, slice):
                start = tel.start if tel.start is not None else 0
                stop = tel.stop if tel.stop is not None else shape[it]
                if start < 0:
                    start == shape[it] + start
                if stop < 0:
                    stop == shape[it] + stop
                if tel.step in [None, 1]:
                    offset.append(start)
                    block.append(stop - start)
                    count.append(1)
                    stride.append(1)
                else:
                    offset.append(start)
                    block.append(1)
                    count.append(
                        int(math.ceil(
                            (stop - start) / float(tel.step))))
                    stride.append(tel.step - 1)
            elif tel is Ellipsis:
                esize = len(shape) - len(t) + 1
                for jt in range(esize):
                    offset.append(0)
                    block.append(shape[it])
                    count.append(1)
                    stride.append(1)
                    if jt < esize - 1:
                        it += 1
        if len(offset):
            return h5cpp.dataspace.Hyperslab(
                offset=offset, block=block, count=count, stride=stride)


pTh = {
    "long": h5cpp.datatype.Integer,
    "str": h5cpp.datatype.kVariableString,
    "unicode": h5cpp.datatype.kVariableString,
    "bool": h5cpp.datatype.kEBool,
    "int": h5cpp.datatype.kInt64,
    "int64": h5cpp.datatype.kInt64,
    "int32": h5cpp.datatype.kInt32,
    "int16": h5cpp.datatype.kInt16,
    "int8": h5cpp.datatype.kInt8,
    "uint": h5cpp.datatype.kInt64,
    "uint64": h5cpp.datatype.kUInt64,
    "uint32": h5cpp.datatype.kUInt32,
    "uint16": h5cpp.datatype.kUInt16,
    "uint8": h5cpp.datatype.kUInt8,
    "float": h5cpp.datatype.kFloat32,
    "float64": h5cpp.datatype.kFloat64,
    "float32": h5cpp.datatype.kFloat32,
    "string": h5cpp.datatype.kVariableString,
}


hTp = {
    h5cpp.datatype.Integer: "long",
    h5cpp.datatype.kVariableString: "string",
    h5cpp._datatype.Class.STRING: "string",
    h5cpp.datatype.kInt64: "int64",
    h5cpp.datatype.kInt32: "int32",
    h5cpp.datatype.kInt16: "int16",
    h5cpp.datatype.kInt8: "int8",
    h5cpp.datatype.kInt64: "uint",
    h5cpp.datatype.kUInt64: "uint64",
    h5cpp.datatype.kUInt32: "uint32",
    h5cpp.datatype.kUInt16: "uint16",
    h5cpp.datatype.kUInt8: "uint8",
    h5cpp.datatype.Float: "float",
    h5cpp.datatype.kFloat64: "float64",
    h5cpp.datatype.kFloat32: "float32",
}


def open_file(filename, readonly=False, libver=None, swmr=False):
    """ open the new file

    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param libver: library version: 'lastest' or 'earliest'
    :type libver: :obj:`str`
    :returns: file object
    :rtype: :class:`H5CppFile`
    """

    fapl = h5cpp.property.FileAccessList()
    # fapl.set_close_degree(h5cpp._property.CloseDegree.STRONG)
    if readonly:
        flag = h5cpp.file.AccessFlags.READONLY
    else:
        flag = h5cpp.file.AccessFlags.READWRITE
    if swmr:
        if hasattr(h5cpp.file.AccessFlags, "SWMRREAD"):
            flag = flag | h5cpp.file.AccessFlags.SWMRREAD
    if libver is None or libver == 'lastest':
        fapl.library_version_bounds(
            h5cpp.property.LibVersion.LATEST,
            h5cpp.property.LibVersion.LATEST)
    return H5CppFile(h5cpp.file.open(filename, flag, fapl), filename)


def create_file(filename, overwrite=False, libver=None):
    """ create a new file

    :param filename: file name
    :type filename: :obj:`str`
    :param overwrite: overwrite flag
    :type overwrite: :obj:`bool`
    :param libver: library version: 'lastest' or 'earliest'
    :type libver: :obj:`str`
    :returns: file object
    :rtype: :class:`H5CppFile`
    """
    fcpl = h5cpp.property.FileCreationList()
    fapl = h5cpp.property.FileAccessList()
    # fapl.set_close_degree(h5cpp._property.CloseDegree.STRONG)
    flag = h5cpp.file.AccessFlags.TRUNCATE if overwrite \
        else h5cpp.file.AccessFlags.EXCLUSIVE
    if libver is None or libver == 'lastest':
        fapl.library_version_bounds(
            h5cpp.property.LibVersion.LATEST,
            h5cpp.property.LibVersion.LATEST)
    fl = h5cpp.file.create(filename, flag, fcpl, fapl)
    rt = fl.root()
    attrs = rt.attributes
    attrs.create("file_time", pTh["unicode"]).write(
        unicode(H5CppFile.currenttime()))
    attrs.create("HDF5_version", pTh["unicode"]).write(u"")
    attrs.create("NX_class", pTh["unicode"]).write(u"NXroot")
    attrs.create("NeXus_version", pTh["unicode"]).write(u"4.3.0")
    attrs.create("file_name", pTh["unicode"]).write(unicode(filename))
    attrs.create("file_update_time", pTh["unicode"]).write(
        unicode(H5CppFile.currenttime()))
    rt.close()
    return H5CppFile(fl, filename)


def link(target, parent, name):
    """ create link

    :param target: nexus path name
    :type target: :obj:`str`
    :param parent: parent object
    :type parent: :class:`FTObject`
    :param name: link name
    :type name: :obj:`str`
    :returns: link object
    :rtype: :class:`H5CppLink`
    """
    if ":/" in target:
        filename, path = target.split(":/")
    else:
        filename, path = None, target

    localfname = H5CppLink.getfilename(parent)
    if filename and \
       os.path.abspath(filename) != os.path.abspath(localfname):
        h5cpp.node.link(target_file=filename,
                        target=h5cpp.Path(path),
                        link_base=parent.h5object,
                        link_path=h5cpp.Path(name))
    else:
        h5cpp.node.link(target=h5cpp.Path(path),
                        link_base=parent.h5object,
                        link_path=h5cpp.Path(name))

    lks = parent.h5object.links
    lk = [e for e in lks if str(e.path.name) == name][0]
    el = H5CppLink(lk, parent)
    return el


def get_links(parent):
    """ get links

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns: list of link objects
    :returns: link object
    :rtype: :obj: `list` <:class:`H5CppLink`>
    """
    lks = parent.h5object.links
    links = [H5CppLink(e, parent) for e in lks]
    return links


def deflate_filter():
    """ create deflate filter

    :returns: deflate filter object
    :rtype: :class:`H5CppDeflate`
    """
    return H5CppDeflate(h5cpp.filter.Deflate())


class H5CppFile(filewriter.FTFile):

    """ file tree file
    """

    def __init__(self, h5object, filename):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param filename:  file name
        :type filename: :obj:`str`
        """
        filewriter.FTFile.__init__(self, h5object, filename)
        #: (:obj:`str`) object nexus path
        self.path = None
        if hasattr(h5object, "path"):
            self.path = h5object.path

    def root(self):
        """ root object

        :returns: parent object
        :rtype: :class:`H5CppGroup`
        """
        return H5CppGroup(self._h5object.root(), self)

    def flush(self):
        """ flash the data
        """
        self._h5object.flush()

    def close(self):
        """ close file
        """
        filewriter.FTFile.close(self)
        if self._h5object.is_valid:
            self._h5object.close()

    @property
    def is_valid(self):
        """ check if file is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._h5object.is_valid

    @property
    def readonly(self):
        """ check if file is readonly

        :returns: readonly flag
        :rtype: :obj:`bool`
        """
        try:
            flag = self._h5object.intent == h5cpp.file.AccessFlags.READONLY
            if not flag and hasattr(h5cpp.file.AccessFlags, "SWMRREAD"):
                    return self._h5object.intent == \
                        h5cpp.file.AccessFlags.READONLY \
                        | h5cpp.file.AccessFlags.SWMRREAD
            else:
                return flag
        except Exception:
            return None

    def reopen(self, readonly=False, swmr=False, libver=None):
        """ reopen file

        :param readonly: readonly flag
        :type readonly: :obj:`bool`
        :param swmr: swmr flag
        :type swmr: :obj:`bool`
        :param libver:  library version, default: 'latest'
        :type libver: :obj:`str`
        """

        fapl = h5cpp.property.FileAccessList()
        # fapl.set_close_degree(h5cpp._property.CloseDegree.STRONG)
        if libver is None or libver == 'lastest' or swmr:
            fapl.library_version_bounds(
                h5cpp.property.LibVersion.LATEST,
                h5cpp.property.LibVersion.LATEST)

        if swmr:
            if not hasattr(h5cpp.file.AccessFlags, "SWMRWRITE"):
                raise Exception("SWMR not supported")
            if not readonly:
                flag = h5cpp.file.AccessFlags.READWRITE \
                       | h5cpp.file.AccessFlags.SWMRWRITE
            else:
                flag = h5cpp.file.AccessFlags.READONLY \
                       | h5cpp.file.AccessFlags.SWMRREAD

        elif readonly:
            flag = h5cpp.file.AccessFlags.READONLY
        else:
            flag = h5cpp.file.AccessFlags.READWRITE
        if self.is_valid:
            self.close()
        self._h5object = h5cpp.file.open(self.name, flag, fapl)
        filewriter.FTFile.reopen(self)


class H5CppGroup(filewriter.FTGroup):

    """ file tree group
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """

        filewriter.FTGroup.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = u""
        #: (:obj:`str`) object name
        self.name = None
        if hasattr(h5object, "link"):
            self.name = h5object.link.path.name
            if tparent and tparent.path:
                if isinstance(tparent, H5CppFile):
                    if self.name == ".":
                        self.path = u"/"
                    else:
                        self.path = u"/" + self.name
                else:
                    if tparent.path.endswith("/"):
                        self.path = tparent.path
                    else:
                        self.path = tparent.path + u"/"
                    self.path += self.name
            if ":" not in self.name:
                if u"NX_class" in [at.name for at in h5object.attributes]:
                    clss = filewriter.first(
                        h5object.attributes["NX_class"]).read()
                else:
                    clss = ""
                if clss:
                    if isinstance(clss, (list, np.ndarray)):
                        clss = clss[0]
                if clss and clss != 'NXroot':
                    self.path += u":" + str(clss)

    def open(self, name):
        """ open a file tree element

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`FTObject`
        """

        try:
            if self._h5object.has_group(h5cpp.Path(name)):
                return H5CppGroup(
                    self._h5object.get_group(h5cpp.Path(name)), self)
            elif self._h5object.has_dataset(h5cpp.Path(name)):
                return H5CppField(
                    self._h5object.get_dataset(h5cpp.Path(name)), self)
            elif self._h5object.attributes.exists(name):
                return H5CppAttribute(self._h5object.attributes[name], self)
            else:
                return H5CppLink(
                    [lk for lk in self._h5object.links
                     if lk.path.name == name][0], self)

        except Exception as e:
            print(str(e))
            return H5CppLink(
                [lk for lk in self._h5object.links
                 if lk.path.name == name][0], self)

    def create_group(self, n, nxclass=None):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param nxclass: group type
        :type nxclass: :obj:`str`
        :returns: file tree group
        :rtype: :class:`H5CppGroup`
        """
        gr = h5cpp.node.Group(self._h5object, n)
        if nxclass is not None:
            gr.attributes.create(
                "NX_class", pTh["unicode"]).write(unicode(nxclass))
        return H5CppGroup(gr, self)

    def create_field(self, name, type_code,
                     shape=None, chunk=None, dfilter=None):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param type_code: nexus field type
        :type type_code: :obj:`str`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param chunk: chunk
        :type chunk: :obj:`list` < :obj:`int` >
        :param dfilter: filter deflater
        :type dfilter: :class:`H5CppDeflate`
        :returns: file tree field
        :rtype: :class:`H5CppField`
        """
        dcpl = h5cpp.property.DatasetCreationList()
        shape = shape or [1]
        dataspace = h5cpp.dataspace.Simple(
            tuple(shape), tuple([h5cpp.dataspace.UNLIMITED] * len(shape)))
        if dfilter:
            dfilter.h5object(dcpl)
            if dfilter.shuffle:
                sfilter = h5cpp.filter.Shuffle()
                sfilter(dcpl)
        if chunk is None and shape is not None:
            chunk = [(dm if dm != 0 else 1) for dm in shape]
        dcpl.layout = h5cpp.property.DatasetLayout.CHUNKED
        dcpl.chunk = tuple(chunk)
        field = h5cpp.node.Dataset(
            self._h5object, h5cpp.Path(name),
            pTh[_tostr(type_code)], dataspace,
            dcpl=dcpl)

        fld = H5CppField(field, self)
        # if type_code == "bool":
        #     fld.boolflag = True
        return fld

    @property
    def size(self):
        """ group size

        :returns: group size
        :rtype: :obj:`int`
        """
        return self._h5object.links.size

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`H5CppAttributeManager`
        """
        return H5CppAttributeManager(self._h5object.attributes, self)

    def close(self):
        """ close group
        """
        filewriter.FTGroup.close(self)

        if self._h5object.is_valid:
            self._h5object.close()

    def reopen(self):
        """ reopen group
        """
        if isinstance(self._tparent, H5CppFile):
            self._h5object = self._tparent.h5object.root()
        else:
            try:
                self._h5object = self._tparent.h5object.get_group(
                    h5cpp.Path(self.name))
            except Exception as e:
                print(str(e))
                self._h5object = [lk for lk in self._tparent.h5object.links
                                  if lk.path.name == self.name][0]
        filewriter.FTGroup.reopen(self)

    def exists(self, name):
        """ if child exists

        :param name: child name
        :type name: :obj:`str`
        :returns: existing flag
        :rtype: :obj:`bool`
        """
        return name in [
            lk.path.name for lk in self._h5object.links]

    def names(self):
        """ read the child names

        :returns: pni object
        :rtype: :obj:`list` <`str`>
        """
        return [
            lk.path.name for lk in self._h5object.links]

    class H5CppGroupIter(object):

        def __init__(self, group):
            """ constructor

            :param group: group object
            :type manager: :obj:`H5CppGroup`
            """

            self.__group = group
            self.__names = group.names()

        def __next__(self):
            """ the next attribute

            :returns: attribute object
            :rtype: :class:`FTAtribute`
            """
            if self.__names:
                return self.__group.open(self.__names.pop(0))
            else:
                raise StopIteration()

        next = __next__

        def __iter__(self):
            """ attribute iterator

            :returns: attribute iterator
            :rtype: :class:`H5CppAttrIter`
            """
            return self

    def __iter__(self):
        """ attribute iterator

        :returns: attribute iterator
        :rtype: :class:`H5CppAttrIter`
        """
        return self.H5CppGroupIter(self)

    @property
    def is_valid(self):
        """ check if field is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._h5object.is_valid


class H5CppField(filewriter.FTField):

    """ file tree file
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        filewriter.FTField.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = None
        if hasattr(h5object, "link"):
            self.name = h5object.link.path.name
            if tparent and tparent.path:
                if tparent.path == "/":
                    self.path = "/" + self.name
                else:
                    self.path = tparent.path + "/" + self.name
        #: (:obj:`bool`) bool flag
        # self.boolflag = False

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`H5CppAttributeManager`
        """
        return H5CppAttributeManager(self._h5object.attributes, self)

    def close(self):
        """ close field
        """
        filewriter.FTField.close(self)
        if self._h5object.is_valid:
            self._h5object.close()

    def reopen(self):
        """ reopen field
        """
        try:
            self._h5object = self._tparent.h5object.get_dataset(
                h5cpp.Path(self.name))
        except Exception:
            self._h5object = [lk for lk in self._tparent.h5object.links
                              if lk.path.name == self.name][0]

        filewriter.FTField.reopen(self)

    def refresh(self):
        """ refresh the field

        :returns: refreshed
        :rtype: :obj:`bool`
        """
        self._h5object.refresh()
        return True

    def grow(self, dim=0, ext=1):
        """ grow the field

        :param dim: growing dimension
        :type dim: :obj:`int`
        :param dim: size of the grow
        :type dim: :obj:`int`
        """
        self._h5object.extent(dim, ext)

    def read(self):
        """ read the field value

        :returns: pni object
        :rtype: :obj:`any`
        """
        if self.dtype in ['string', b'string']:
            # workaround for bug: h5cpp #355
            if self.size == 0:
                if self.shape:
                    v = np.empty(shape=self.shape,
                                 dtype=nptype(self.dtype))
                else:
                    v = []
            else:
                v = self._h5object.read()
            try:
                v = v.decode('UTF-8')
            except Exception:
                pass
        else:
            v = self._h5object.read()
        return v

    def write(self, o):
        """ write the field value

        :param o: pni object
        :type o: :obj:`any`
        """
        self._h5object.write(o)

    def __setitem__(self, t, o):
        """ set value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: pni object
        :type o: :obj:`any`
        """
        if self.shape == (1,) and t == 0:
            return self._h5object.write(o)
        selection = _slice2selection(t, self.shape)
        if selection is None:
            self._h5object.write(o)
        else:
            self._h5object.write(o, selection=selection)

    def __getitem__(self, t):
        """ get value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: pni object
        :rtype: :obj:`any`
        """
        if self.shape == (1,) and t == 0:
            if self.dtype in ['string', b'string']:
                # workaround for bug: h5cpp #355
                if self.size == 0:
                    if self.shape:
                        v = np.empty(shape=self.shape, dtype=self.dtype)
                    else:
                        v = []
                else:
                    v = self._h5object.read()
            else:
                v = self._h5object.read()

        selection = _slice2selection(t, self.shape)
        if selection is None:
            if self.dtype in ['string', b'string']:
                # workaround for bug: h5cpp #355
                if self.size == 0:
                    if self.shape:
                        v = np.empty(shape=self.shape, dtype=self.dtype)
                    else:
                        v = []
                else:
                    v = self._h5object.read()
                try:
                    v = v.decode('UTF-8')
                except Exception:
                    pass
            else:
                v = self._h5object.read()
            return v
        v = self._h5object.read(selection=selection)
        # if hasattr(v, "shape") and hasattr(v, "reshape"):
        #     shape = [sh for sh in v.shape if sh != 1]
        #     if shape != list(v.shape):
        #         v.reshape(shape)
        if hasattr(v, "shape"):
            shape = v.shape
            if len(shape) == 3 and shape[2] == 1:
                #: problem with old numpy
                # v.reshape(shape[:2])
                v = v[:, :, 0]
                shape = v.shape
            if len(shape) == 3 and shape[1] == 1:
                # v.reshape([shape[0], shape[2]])
                v = v[:, 0, :]
                shape = v.shape
            if len(shape) == 3 and shape[0] == 1:
                # v.reshape([shape[1], shape[2]])
                v = v[0, :, :]
                shape = v.shape
            if len(shape) == 2 and shape[1] == 1:
                # v.reshape([shape[0]])
                v = v[0, :]
                shape = v.shape
            if len(shape) == 2 and shape[0] == 1:
                # v.reshape([shape[1]])
                v = v[:, 0]
                shape = v.shape
            if len(shape) == 1 and shape[0] == 1:
                v = v[0]
        if self.dtype in ['string', b'string']:
            try:
                v = v.decode('UTF-8')
            except Exception:
                pass
        return v

    @property
    def is_valid(self):
        """ check if field is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._h5object.is_valid

    @property
    def dtype(self):
        """ field data type

        :returns: field data type
        :rtype: :obj:`str`
        """
        # if self.boolflag:
        #     return "bool"
        if str(self._h5object.datatype.type) == "FLOAT":
            if self._h5object.datatype.size == 8:
                return "float64"
            elif self._h5object.datatype.size == 4:
                return "float32"
            elif self._h5object.datatype.size == 16:
                return "float128"
            else:
                return "float"
        elif str(self._h5object.datatype.type) == "INTEGER":

            if self._h5object.datatype.size == 8:
                if self._h5object.datatype.is_signed():
                    return "int64"
                else:
                    return "uint64"
            elif self._h5object.datatype.size == 4:
                if self._h5object.datatype.is_signed():
                    return "int32"
                else:
                    return "uint32"
            elif self._h5object.datatype.size == 2:
                if self._h5object.datatype.is_signed():
                    return "int16"
                else:
                    return "uint16"
            elif self._h5object.datatype.size == 1:
                if self._h5object.datatype.is_signed():
                    return "int8"
                else:
                    return "uint8"
            elif self._h5object.datatype.size == 16:
                if self._h5object.datatype.is_signed():
                    return "int128"
                else:
                    return "uint128"
            else:
                return "int"
        elif str(self._h5object.datatype.type) == "ENUM":
            if h5cpp._datatype.is_bool(
                    h5cpp.datatype.Enum(self._h5object.datatype)):
                return "bool"
            else:
                return "int"

        return hTp[self._h5object.datatype.type]
#

    @property
    def shape(self):
        """ field shape

        :returns: field shape
        :rtype: :obj:`list` < :obj:`int` >
        """
        if hasattr(self._h5object.dataspace, "current_dimensions"):
            return self._h5object.dataspace.current_dimensions
        else:
            return (1,)

    @property
    def size(self):
        """ field size

        :returns: field size
        :rtype: :obj:`int`
        """
        return self._h5object.dataspace.size


class H5CppLink(filewriter.FTLink):

    """ file tree link
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        filewriter.FTLink.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = None
        if tparent and tparent.path:
            self.path = tparent.path
        if not self.path.endswith("/"):
            self.path += "/"
        self.name = h5object.path.name
        self.path += self.name

    @property
    def is_valid(self):
        """ check if link is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        try:
            return self._h5object.node.is_valid
        except Exception:
            return False

    def refresh(self):
        """ refresh the field

        :returns: refreshed
        :rtype: :obj:`bool`
        """
        self._h5object.refresh()
        return True

    @classmethod
    def getfilename(cls, obj):
        filename = ""
        while not filename:
            par = obj.parent
            if par is None:
                break
            if isinstance(par, H5CppFile):
                filename = par.name
                break
            else:
                obj = par
        return filename

    @property
    def target_path(self):
        """ target path

        :returns: target path
        :rtype: :obj:`str`
        """
        fpath = self._h5object.target().file_path
        opath = self._h5object.target().object_path
        if not fpath:
            fpath = self.getfilename(self)
        return "%s:/%s" % (fpath, opath)

    def reopen(self):
        """ reopen field
        """
        lks = self._tparent.h5object.links
        try:
            lk = [e for e in lks
                  if e.path.name == self.name][0]
            self._h5object = lk
        except Exception:
            self._h5object = None
        filewriter.FTLink.reopen(self)

    def close(self):
        """ close group
        """
        filewriter.FTLink.close(self)
        self._h5object = None


class H5CppDeflate(filewriter.FTDeflate):

    """ file tree deflate
    """

    def __init__(self, h5object):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        """
        filewriter.FTDeflate.__init__(self, h5object)
        self.__shuffle = False

    def __getrate(self):
        """ getter for compression rate

        :returns: compression rate
        :rtype: :obj:`int`
        """
        return self._h5object.level

    def __setrate(self, value):
        """ setter for compression rate

        :param value: compression rate
        :type value: :obj:`int`
        """
        self._h5object.level = value

    #: (:obj:`int`) compression rate
    rate = property(__getrate, __setrate)

    def __getshuffle(self):
        """ getter for compression shuffle

        :returns: compression shuffle
        :rtype: :obj:`bool`
        """
        return self.__shuffle

    def __setshuffle(self, value):
        """ setter for compression shuffle

        :param value: compression shuffle
        :type value: :obj:`bool`
        """
        self.__shuffle = value

    #: (:obj:`bool`) compression shuffle
    shuffle = property(__getshuffle, __setshuffle)


class H5CppAttributeManager(filewriter.FTAttributeManager):

    """ file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        filewriter.FTAttributeManager.__init__(self, h5object, tparent)
        #: (:obj:`str`) object nexus path
        self.path = ''
        #: (:obj:`str`) object name
        self.name = None

    def create(self, name, dtype, shape=None, overwrite=False):
        """ create a new attribute

        :param name: attribute name
        :type name: :obj:`str`
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param shape: attribute shape
        :type shape: :obj:`list` < :obj:`int` >
        :param overwrite: overwrite flag
        :type overwrite: :obj:`bool`
        :returns: attribute object
        :rtype: :class:`H5CppAtribute`
        """
        names = [at.name for at in self._h5object]
        if name in names:
            if overwrite:
                self._h5object.remove(name)
            else:
                raise Exception("Attribute %s exists" % name)
        shape = shape or []
        if shape:
            at = self._h5object.create(name, pTh[_tostr(dtype)], shape)
            if dtype in ['string', b'string']:
                emp = np.empty(shape, dtype="unicode")
                emp[:] = ''
                at.write(emp)
            else:
                at.write(np.zeros(shape, dtype=dtype))
        else:
            at = self._h5object.create(name, pTh[_tostr(dtype)])
            if dtype in ['string', b'string']:
                at.write(np.array(u"", dtype="unicode"))
            else:
                at.write(np.array(0, dtype=dtype))

        at = H5CppAttribute(at, self.parent)
        # if dtype == "bool":
        #     at.boolflag = True
        return at

    def __len__(self):
        """ number of attributes

        :returns: number of attributes
        :rtype: :obj:`int`
        """
        return self._h5object.__len__()

    def __getitem__(self, name):
        """ get value

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute object
        :rtype: :class:`FTAtribute`
        """
        return H5CppAttribute(
            self._h5object.__getitem__(name), self.parent)

    def close(self):
        """ close attribure manager
        """
        filewriter.FTAttributeManager.close(self)

    def reopen(self):
        """ reopen field
        """
        self._h5object = self._tparent.h5object.attributes
        filewriter.FTAttributeManager.reopen(self)

    @property
    def is_valid(self):
        """ check if link is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._tparent.h5object.is_valid


class H5CppAttribute(filewriter.FTAttribute):

    """ file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        filewriter.FTAttribute.__init__(self, h5object, tparent)
        #: (:obj:`str`) object name
        self.name = h5object.name
        #: (:obj:`str`) object nexus path
        self.path = tparent.path
        self.path += "@%s" % self.name

        #: (:obj:`bool`) bool flag
        # self.boolflag = False

    def close(self):
        """ close attribute
        """
        filewriter.FTAttribute.close(self)
        if self._h5object.is_valid:
            self._h5object.close()

    def read(self):
        """ read attribute value

        :returns: python object
        :rtype: :obj:`any`
        """
        vl = self._h5object.read()
        if self.dtype in ['string', b'string']:
            try:
                vl = vl.decode('UTF-8')
            except Exception:
                pass
        return vl

    def write(self, o):
        """ write attribute value

        :param o: python object
        :type o: :obj:`any`
        """
        self._h5object.write(o)

    def __setitem__(self, t, o):
        """ write attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: python object
        :type o: :obj:`any`
        """
        if t is Ellipsis or t == slice(None, None, None) or \
           t == (slice(None, None, None), slice(None, None, None)) or \
           (hasattr(o, "__len__") and t == slice(0, len(o), None)):
            if self.dtype in ['string', b'string']:
                if isinstance(o, str):
                    self._h5object.write(unicode(o))
                else:
                    dtype = np.unicode_
                    self._h5object.write(np.array(o, dtype=dtype))
            else:
                self._h5object.write(np.array(o, dtype=self.dtype))
        elif isinstance(t, slice):
            var = self._h5object.read()
            if self.dtype not in ['string', b'string']:
                var[t] = np.array(o, dtype=nptype(self.dtype))
            else:
                dtype = np.unicode_
                var[t] = np.array(o, dtype=dtype)
                var = var.astype(dtype)
            try:
                self._h5object.write(var)
            except Exception:
                dtype = np.unicode_
                tvar = np.array(var, dtype=dtype)
                self._h5object[0][self.name] = tvar

        elif isinstance(t, tuple):
            var = self._h5object.read()
            if self.dtype not in ['string', b'string']:
                var[t] = np.array(o, dtype=nptype(self.dtype))
            else:
                dtype = np.unicode_
                if hasattr(var, "flatten"):
                    vv = var.flatten().tolist() + \
                        np.array(o, dtype=dtype).flatten().tolist()
                    nt = np.array(vv, dtype=dtype)
                    var = np.array(var, dtype=nt.dtype)
                    var[t] = np.array(o, dtype=dtype)
                elif hasattr(var, "tolist"):
                    var = var.tolist()
                    var[t] = np.array(o, dtype=self.dtype).tolist()
                else:
                    var[t] = np.array(o, dtype=self.dtype).tolist()
                var = var.astype(dtype)
            self._h5object.write(var)
        else:
            if isinstance(o, str) or isinstance(o, unicode):
                self._h5object.write(unicode(o))
            else:
                self._h5object.write(np.array(o, dtype=self.dtype))

    def __getitem__(self, t):
        """ read attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: python object
        :rtype: :obj:`any`
        """
        v = self._h5object.__getitem__(t)
        # if hasattr(v, "shape") and hasattr(v, "reshape"):
        #     shape = [sh for sh in v.shape if sh != 1]
        #     if shape != list(v.shape):
        #         v.reshape(shape)
        if hasattr(v, "shape"):
            shape = v.shape
            if len(shape) == 3 and shape[2] == 1:
                #: problem with old numpy
                # v.reshape(shape[:2])
                v = v[:, :, 0]
                shape = v.shape
            if len(shape) == 3 and shape[1] == 1:
                # v.reshape([shape[0], shape[2]])
                v = v[:, 0, :]
                shape = v.shape
            if len(shape) == 3 and shape[0] == 1:
                # v.reshape([shape[1], shape[2]])
                v = v[0, :, :]
                shape = v.shape
            if len(shape) == 2 and shape[1] == 1:
                # v.reshape([shape[0]])
                v = v[0, :]
                shape = v.shape
            if len(shape) == 2 and shape[0] == 1:
                # v.reshape([shape[1]])
                v = v[:, 0]
                shape = v.shape
            if len(shape) == 1 and shape[0] == 1:
                v = v[0]
        if self.dtype in ['string', b'string']:
            try:
                v = v.decode('UTF-8')
            except Exception:
                pass
        return v

    @property
    def is_valid(self):
        """ check if attribute is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return self._h5object.is_valid

    @property
    def dtype(self):
        """ field data type

        :returns: field data type
        :rtype: :obj:`str`
        """
        # if self.boolflag:
        #     return "bool"
        if str(self._h5object.datatype.type) == "FLOAT":
            if self._h5object.datatype.size == 8:
                return "float64"
            elif self._h5object.datatype.size == 4:
                return "float32"
            elif self._h5object.datatype.size == 16:
                return "float128"
            else:
                return "float"
        elif str(self._h5object.datatype.type) == "INTEGER":
            if self._h5object.datatype.size == 8:
                if self._h5object.datatype.is_signed():
                    return "int64"
                else:
                    return "uint64"
            elif self._h5object.datatype.size == 4:
                if self._h5object.datatype.is_signed():
                    return "int32"
                else:
                    return "uint32"
            elif self._h5object.datatype.size == 2:
                if self._h5object.datatype.is_signed():
                    return "int16"
                else:
                    return "uint16"
            elif self._h5object.datatype.size == 1:
                if self._h5object.datatype.is_signed():
                    return "int8"
                else:
                    return "uint8"
            elif self._h5object.datatype.size == 16:
                if self._h5object.datatype.is_signed():
                    return "int128"
                else:
                    return "uint128"
            else:
                return "int"
        elif str(self._h5object.datatype.type) == "ENUM":
            if h5cpp._datatype.is_bool(
                    h5cpp.datatype.Enum(self._h5object.datatype)):
                return "bool"
            else:
                return "int"
        return hTp[self._h5object.datatype.type]

    @property
    def shape(self):
        """ attribute shape

        :returns: attribute shape
        :rtype: :obj:`list` < :obj:`int` >
        """
        if hasattr(self._h5object.dataspace, "current_dimensions"):
            return self._h5object.dataspace.current_dimensions
        else:
            return (1,)

    def reopen(self):
        """ reopen attribute
        """
        self._h5object = self._tparent.h5object.attributes[self.name]
        filewriter.FTAttribute.reopen(self)
