import numpy as np
import torch
from torch.utils.data.sampler import SubsetRandomSampler
from collections import defaultdict
import pickle

assert (np.version.version >= '1.17.0')

from PIL import Image
import time


# from PIL import Image

class gntReader(torch.utils.data.Dataset):
    gnt_head = np.dtype('u4, <u2, u2, u2')

    def __init__(self, file=None, transform=lambda x: x):
        self.transform = transform
        self.glyph_to_code = {}
        self.glyph_to_images = defaultdict(list)
        self.code_to_glyph = []
        self.X = []
        self.y = []

        self.max_width = 0
        self.max_height = 0

        if file != None:
            self.load_from_file(file)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, index):
        return self.transform(self.X[index]), self.y[index]

    def add(self, path):
        with open(path, mode='rb') as file:
            while (self._read(file)): pass

    def _read(self, file):
        head_buffer = file.read(self.gnt_head.itemsize)
        if (len(head_buffer) == 0):
            return False
        head = np.frombuffer(head_buffer, dtype=self.gnt_head)
        size, tag, width, height = head[0]
        if width > self.max_width: self.max_width = width
        if height > self.max_height: self.max_height = height
        glyph = tag.tobytes().decode('gb2312')  # gb2312-80

        img = np.frombuffer(file.read(width * height), dtype=np.uint8)
        img = img.reshape(height, width)

        self._add_pair(img, glyph)
        return True

    def _add_pair(self, img, glyph):
        if glyph in self.glyph_to_code:
            code = self.glyph_to_code[glyph]
        else:
            code = np.int64(len(self.code_to_glyph))
            self.code_to_glyph.append(glyph)
            self.glyph_to_code[glyph] = code

        self.glyph_to_images[glyph].append(len(self.X))

        self.X.append(img)
        self.y.append(code)

    def shuffle_and_split(self, ratio, num_of_classes = -1, **kwargs):
        indices = list(range(len(self)))
        if num_of_classes > 0:
            indices = [x for x in indices if self.y[x] < num_of_classes]
        np.random.shuffle(indices)
        split = round(ratio * len(indices))
        first_indices, second_indices = indices[split:], indices[:split]
        first_sampler = SubsetRandomSampler(first_indices)
        second_sampler = SubsetRandomSampler(second_indices)
        first_loader = torch.utils.data.DataLoader(self, sampler=first_sampler, **kwargs)
        second_loader = torch.utils.data.DataLoader(self, sampler=second_sampler, **kwargs)
        return first_loader, second_loader

    def save_to_file(self, file):
        with open(file, 'wb') as handle:
            saver = [self.X, self.y, self.glyph_to_code, self.glyph_to_images, self.code_to_glyph]
            pickle.dump(saver, handle)

    def load_from_file(self, file):
        with open(file, 'rb') as handle:
            saver = pickle.load(handle)
            self.X, self.y, self.glyph_to_code, self.glyph_to_images, self.code_to_glyph = saver

