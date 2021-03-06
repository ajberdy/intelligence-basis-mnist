"""
some science
"""
import itertools
import math

import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np


class Offset:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if other == 0:
            return self.x == self.y == 0
        return self.x == other[0] and self.y == other[1]

    def __getitem__(self, item):
        if item == 0:
            return self.x
        if item == 1:
            return self.y
        raise IndexError()


class Pixel:
    """ zero-order pixelgram """

    def __init__(self, pixel: float):
        self.pixel = pixel

    def __repr__(self):
        return f"Pixel({self.pixel:.2f})"

    def alignment(self, other):
        if self.pixel == other.pixel:
            return 1
        return max(0, 1 - 2 * abs(self.pixel - other.pixel) / (self.pixel + other.pixel))

    def adjust(self, other, weight=.5):
        self.pixel = (1 - weight) * self.pixel + weight * other.pixel

    def copy(self):
        return Pixel(self.pixel)

    def __hash__(self):
        return hash(self.pixel)

    def __eq__(self, other):
        if not isinstance(other, Pixel):
            raise NotImplementedError()
        return self.pixel == other.pixel

    def __mul__(self, other):
        return self.alignment(other)

    def __rmul__(self, other):
        return self * other


class PosPixel(Pixel):
    """ fixed-position pixel """

    def __init__(self, pixel, ix):
        self.r = ix // 28
        self.c = ix % 28
        super().__init__(pixel)

    def __repr__(self):
        return f"PosPixel({self.pixel:.2f})_[{self.r:.2f}, {self.c:.2f}]"

    def alignment(self, other):
        pos_alignment = (1 - math.sqrt((self.r - other.r)**2 + (self.c - other.c)**2) / (28 * math.sqrt(2)))
        intense_alignment = super().alignment(other)
        pos_relative_sig = .5
        return (1 - pos_relative_sig) * intense_alignment + pos_relative_sig * pos_alignment

    def adjust(self, other, weight=.5):
        self.pixel = (1 - weight) * self.pixel + weight * other.pixel
        self.r = (1 - weight) * self.r + weight * other.r
        self.c = (1 - weight) * self.c + weight * other.c

    def __hash__(self):
        return hash((self.pixel, self.r, self.c))


def mutual_info_alignment_prior(images):
    """
    for every pair of pixels, compute their mutual information

    Sum over all images:
        P(x, y) log (p(x,y) / p(x)p(y))
    """
    pass

    # flat_images = np.array([image.flatten() for image in images])
    # mi_scores = np.zeros([784, 784])
    # for ix in range(12):
    #     if not ix % 10:
    #         print(ix, end=', ', flush=True)
    #
    #     mi_scores[ix] = mutual_info_classif(flat_images, images[:, ix])
    # return mi_scores


class PixelgramLearner:

    def __init__(self, epsilon=0.1):
        self.epsilon = epsilon
        self.known_grams = set()
        self._weights = {}
        self.min_weight = self.epsilon * 10

    @property
    def iterbasis(self):
        return sorted(self._weights.items(), key=lambda x: x[1], reverse=True)

    def learn_zero_order(self, images):
        for image in images:
            for pix in image.flat:
                pixel = Pixel(pix)
                what_it_was, how_closely = self.what_is_this(pixel)

                if how_closely > 1 - self.epsilon:
                    self.this_is_that(pixel, what_it_was, how_closely)
                else:
                    self.this_is_new(pixel)

    def learn_zero_order_pos(self, images):
        for i_ix, image in enumerate(images):
            print(i_ix, end=',', flush=True)
            for ix, pix in enumerate(image.flat):
                pixel = PosPixel(pix, ix)
                what_it_was, how_closely = self.what_is_this(pixel)

                if how_closely > 1 - self.epsilon:
                    self.this_is_that(pixel, what_it_was, how_closely)
                else:
                    self.this_is_new(pixel)

            to_remove = set()
            for gram, weight in self._weights.items():
                if weight < self.min_weight:
                    to_remove.add(gram)

            while to_remove:
                gram = to_remove.pop()
                del self._weights[gram]
                self.known_grams.remove(gram)

        print("done")

    def what_is_this(self, pixel_cluster):
        """
        out of what is known, what could this thing be

        in order of awareness priority:
            if above a threshold:
                choose it
                keep searching for a little
                if you find something better
                    choose it and keep searching a little

        """
        sureness = 1 - self.epsilon
        choice = None
        epsilon_sure = .001

        for gram in sorted(self.known_grams, key=self._weights.get, reverse=True):
            alignment = gram.alignment(pixel_cluster)
            if alignment > sureness:
                sureness = alignment
                choice = gram
            else:
                if choice:
                    sureness += alignment * (1 - sureness)

            if sureness > 1 - epsilon_sure:
                return choice, sureness

        return choice, sureness

    def this_is_that(self, this: Pixel, that: Pixel, by_how_much: float):
        """
        we've decided that this is that, now adjust our knowledge accordingly

        """
        weight = self._weights[that]
        del self._weights[that]
        self.known_grams.remove(that)
        that.adjust(this, weight=by_how_much/(weight + by_how_much))
        self._weights[that] = weight + by_how_much
        self.known_grams.add(that)

    def this_is_new(self, pixel):
        """
        we learned a new thing
        """
        self.known_grams.add(pixel)
        self._weights[pixel] = self.epsilon


def show_mnist(label, image, show=True):
    pixels = image.reshape((28, 28))
    # Plot
    plt.title('Label is {label}'.format(label=label))
    plt.imshow(pixels, cmap='gray')
    if show:
        plt.show()


def show_filters(image, pixels, weights, show=True):
    pixels = iter(pixels)
    r, c = 2, 3
    fig, axes = plt.subplots(r, c)
    fig.tight_layout()
    pixels = sorted(pixels, key=weights.get, reverse=True)
    for pixel, (x, y) in zip(pixels, itertools.product(range(r), range(c))):
        activations = np.array([pixel.alignment(Pixel(x)) for x in image.flat]).reshape([28, 28])
        axes[x,y].contourf(np.arange(28), np.arange(27, -1, -1), activations, cmap=cm.coolwarm)
        axes[x,y].set_title(f"{pixel}: weight = {weights[pixel]:.2f}", fontsize=8)
    if show:
        plt.show()


def show_pos_filters(image, pgl, show=True):
    r, c = 5, 5
    fig, axes = plt.subplots(r, c, figsize=(10, 10))
    fig.tight_layout()
    for (pixel, weight), (x, y) in zip(pgl.iterbasis, itertools.product(range(r), range(c))):
        activations = np.array([pixel.alignment(PosPixel(x, ix)) for ix, x in enumerate(image.flat)]).reshape([28, 28])
        axes[x,y].contourf(np.arange(28), np.arange(27, -1, -1), activations, cmap=cm.coolwarm)
        axes[x,y].set_title(f"{pixel}: weight = {weight:.2f}", fontsize=8)
    if show:
        plt.show()


def show_basis_segmentation(image, pgl: PixelgramLearner, show=True):
    coloriter = list(iter(cm.tab10(np.linspace(0, 1, 10))))
    what_are_they = np.empty(784)
    heatmap = np.empty([784, 4])

    basis_ixs = dict((b, i) for i, (b, __) in enumerate(pgl.iterbasis))

    for i, pixel in enumerate(image.flat):
        what_is, how_much = pgl.what_is_this(PosPixel(pixel, i))
        what_are_they[i] = basis_ixs[what_is] if what_is is not None else -1
        if what_is is None or what_are_they[i] >= 10:
            heatmap[i] = [0, 0, 0, 1]
        else:
            heatmap[i] = coloriter[basis_ixs[what_is]]
            # heatmap[i][3] = .5 * (1 + how_much)

    # heatmap = heatmap.reshape([28,28,4])
    # for i, color in enumerate(coloriter):
    #     heatmap[:, 2*i:2*i + 2] = color

    plt.imshow(heatmap.reshape([28, 28, 4]))
    # plt.colorbar(shrink=0.5, spacing='proportional')
    if show:
        plt.show()


def activation(x, y):
    if x == y:
        return 1
    return max(0, 1 - 2 * abs(x - y) / (x + y))


def visualize_alignments():
    # plt.ion()
    plt.cla()
    fig = plt.figure()
    ax = fig.gca()

    X = np.arange(0, 256, 1)
    Y = np.arange(0, 256, 1)
    Z = np.empty([256, 256])
    for i, j in itertools.product(range(256), repeat=2):
        Z[i][j] = Pixel(i).alignment(Pixel(j))

    surf = ax.contourf(X, Y, Z, cmap=cm.coolwarm)

    fig.colorbar(surf, shrink=0.5, spacing='proportional')
    plt.title("Pixel Alignment Prior")

    plt.show()


def visualize_pos_alignments():
    # plt.ion()
    # plt.cla()
    fig, axes = plt.subplots(10, 10)

    X = np.arange(0, 28, 1)
    Y = np.arange(0, 28, 1)
    Z = np.empty([28, 28])

    for iix, intensity in enumerate(np.linspace(0, 1, 10)):
        for jix, other_intensity in enumerate(np.linspace(0, 1, 10)):
            for i, j in itertools.product(range(28), repeat=2):
                Z[i][j] = PosPixel(other_intensity, i*28 + j).alignment(PosPixel(intensity, 406))
            surf = axes[iix, jix].contourf(X, Y, Z, cmap=cm.coolwarm)


    plt.suptitle("Pixel Positional Alignment Prior")

    plt.show()
