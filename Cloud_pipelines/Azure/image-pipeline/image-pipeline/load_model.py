#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thursday Apr 25 16:45:28 2019

@author: "Anirban Das"
"""

import mxnet as mx
import numpy as np
import cv2
from timeit import default_timer as timer
from collections import namedtuple
Batch = namedtuple('Batch', ['data'])


class ImagenetModel(object):

    #Loads a pre-trained model and returns a MXNet graph
    def __init__(self, synset_path, network_prefix, context=mx.cpu(),
                 label_names=['prob_label'], input_shapes=[('data', (1, 3, 224, 224))]):

        # Load the symbols for the networks from given path
        with open(synset_path, 'r') as f:
            self.synsets = [l.rstrip() for l in f]

        # Load the network parameters from default epoch 0
        sym, arg_params, aux_params = mx.model.load_checkpoint(network_prefix, 0)

        # Load the network into an MXNet module and bind the corresponding parameters
        self.mod = mx.mod.Module(symbol=sym, label_names=label_names, context=context)
        self.mod.bind(for_training=False, data_shapes=input_shapes)
        self.mod.set_params(arg_params, aux_params)

    def predict_from_image(self, cvimage, reshape=(224, 224), N=5):
        topN = []

        # Switch RGB to BGR format (which ImageNet networks take)
        img = cv2.cvtColor(cvimage, cv2.COLOR_BGR2RGB)
        if img is None:
            return topN
        
        
        img = cv2.resize(img, reshape)
        img = img.transpose((2, 0, 1)) # Channel first
        img = img[np.newaxis, :]
        img = img.astype('float32') # for gpu context

        self.mod.forward(Batch([mx.nd.array(img)]))
        #self.mod.forward(Batch([img]))
        prob = self.mod.get_outputs()[0].asnumpy()
        prob = np.squeeze(prob)

        a = np.argsort(prob)[::-1]
        for i in a[0:N]:
            topN.append((prob[i], self.synsets[i]))
        return topN