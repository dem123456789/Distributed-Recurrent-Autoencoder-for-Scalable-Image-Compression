import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import config
from data import extract_patches_2d, reconstruct_from_patches_2d
from utils import RGB_to_L, L_to_RGB
from modules import Cell, Quantizer

device = config.PARAM['device']
code_size = config.PARAM['code_size']
activation = config.PARAM['activation']
num_node = config.PARAM['num_node']

class Encoder(nn.Module):
    def __init__(self):
        super(Encoder, self).__init__()
        self.encoder_info = self.make_encoder_info()
        self.encoder = self.make_encoder()
        
    def make_encoder_info(self):
        encoder_info = [
        {'input_size':3,'output_size':32,'num_layer':1,'cell':'BasicCell','mode':'fc','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'down','scale_factor':2},        
        {'input_size':128,'output_size':128,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'down','scale_factor':2},          
        {'input_size':512,'output_size':128,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'down','scale_factor':2},
        {'input_size':512,'output_size':128,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False}, 
        {'input_size':128,'output_size':code_size,'num_layer':1,'cell':'BasicCell','mode':'fc','normalization':'none','activation':'tanh','raw':False}        
        ]
        return encoder_info

    def make_encoder(self):
        encoder = nn.ModuleDict({})
        for i in range(num_node['E']):
            encoder[str(i)] = nn.ModuleList([])
            for j in range(len(self.encoder_info)):
                encoder[str(i)].append(Cell(self.encoder_info[j]))
        return encoder
        
    def forward(self, input, label, protocol):
        if(protocol['byclass']):
            x = [None for i in range(len(protocol['node_name']['E']))]
            output = None
            for i in range(len(protocol['node_name']['E'])):
                if(input[label==i].size(0)==0):
                    continue
                x[i] = input[label==i]
                x[i] = L_to_RGB(x[i]) if (protocol['img_mode'] == 'L') else x[i]
                node_name = str(protocol['node_name']['E'][i])
                for j in range(len(self.encoder[node_name])):
                    x[i] = self.encoder[node_name][j](x[i])
                output = input.new_zeros(input.size(0),*x[i].size()[1:]) if(output is None) else output
                output[label==i] = x[i]
            output = input if(output is None) else output
        else:
            x = list(input.chunk(len(protocol['node_name']['E']),dim=0))
            for i in range(len(x)):
                x[i] = L_to_RGB(x[i]) if (protocol['img_mode'] == 'L') else x[i]
                node_name = str(protocol['node_name']['E'][i])
                for j in range(len(self.encoder[node_name])):
                    x[i] = self.encoder[node_name][j](x[i])
            output = torch.cat(x,dim=0)
        return output
        
class Decoder(nn.Module):
    def __init__(self):
        super(Decoder, self).__init__()
        self.decoder_info = self.make_decoder_info()
        self.decoder = self.make_decoder()
        
    def make_decoder_info(self):
        decoder_info = [
        {'input_size':code_size,'output_size':128,'num_layer':1,'cell':'BasicCell','mode':'fc','normalization':'none','activation':activation,'raw':False},      
        {'input_size':128,'output_size':512,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'up','scale_factor':2},
        {'input_size':128,'output_size':512,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'up','scale_factor':2},
        {'input_size':128,'output_size':128,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'cell':'ShuffleCell','mode':'up','scale_factor':2},
        {'input_size':32,'output_size':3,'num_layer':1,'cell':'BasicCell','mode':'fc','normalization':'none','activation':'tanh','raw':False},        
        ]
        return decoder_info

    def make_decoder(self):
        decoder = nn.ModuleDict({})
        for i in range(num_node['D']):
            decoder[str(i)] = nn.ModuleList([])
            for j in range(len(self.decoder_info)):
                decoder[str(i)].append(Cell(self.decoder_info[j]))
        return decoder
        
    def forward(self, input, protocol):
        x = list(input.chunk(len(protocol['node_name']['D']),dim=0))
        for i in range(len(x)):
            for j in range(len(self.decoder[protocol['node_name']['D'][i]])):
                x[i] = self.decoder[protocol['node_name']['D'][i]][j](x[i])
            x[i] = RGB_to_L(x[i]) if (protocol['img_mode'] == 'L') else x[i]
        x = torch.cat(x,dim=0)
        return x
        
class Codec(nn.Module):
    def __init__(self):
        super(Codec, self).__init__()
        self.encoder = Encoder()
        self.quantizer = Quantizer()
        self.decoder = Decoder()
        
    def compression_loss_fn(self, input, output, protocol):
        if(protocol['loss_mode']['compression'] == 'bce'):
            loss_fn = F.binary_cross_entropy
        elif(protocol['loss_mode']['compression'] == 'mse'):
            loss_fn = F.mse_loss
        elif(protocol['loss_mode']['compression'] == 'mae'):
            loss_fn = F.l1_loss
        else:
            raise ValueError('compression loss mode not supported') 
        if(protocol['tuning_param']['compression'] > 0):
            loss = loss_fn(output['compression']['img'],input['img'],reduction='sum')
            loss = loss/input['img'].size(0)
            loss = loss.mean()
        else:
            loss = torch.tensor(0,device=device,dtype=torch.float32) 
        return loss

class Classifier(nn.Module):
    def __init__(self, classes_size):
        super(Classifier, self).__init__()
        self.classes_size = classes_size
        self.classifier_info = self.make_classifier_info()
        self.classifier = self.make_classifier()
        
    def make_classifier_info(self):
        classifier_info = [ 
        {'input_size':code_size,'output_size':512,'num_layer':1,'cell':'BasicCell','mode':'pass','normalization':'none','activation':activation,'raw':False},
        {'input_size':512,'output_size':self.classes_size,'num_layer':1,'cell':'BasicCell','mode':'fc','normalization':'none','activation':'none','raw':False},
        {'cell':'PoolCell','mode':'avg','output_size':1}
        ]
        return classifier_info

    def make_classifier(self):
        classifier = nn.ModuleList([])
        for i in range(len(self.classifier_info)):
            classifier.append(Cell(self.classifier_info[i]))
        return classifier
        
    def classification_loss_fn(self, input, output, protocol):
        if(protocol['loss_mode']['classification'] == 'ce'):
            loss_fn = F.cross_entropy
        else:
            raise ValueError('classification loss mode not supported')
        if(protocol['tuning_param']['classification'] > 0):
            loss = loss_fn(output['classification'],input['label'],reduction='mean')
            loss = loss.mean()
        else:
            loss = torch.tensor(0,device=device,dtype=torch.float32) 
        return loss
        
    def forward(self, input, protocol):
        x = input
        for i in range(len(self.classifier)):
            x = self.classifier[i](x)        
        x = x.view(x.size(0),self.classes_size)
        return x
        
class shuffle_codec(nn.Module):
    def __init__(self,classes_size):
        super(shuffle_codec, self).__init__()
        self.classes_size = classes_size
        self.codec = Codec()
        self.classifier = Classifier(classes_size)
        
    def forward(self, input, protocol):
        output = {'loss':torch.tensor(0,device=device,dtype=torch.float32),
                'compression':{'img':torch.tensor(0,device=device,dtype=torch.float32),'code':[]},
                'classification':torch.tensor(0,device=device,dtype=torch.float32)}  
        
        compression_loss = torch.tensor(0,device=device,dtype=torch.float32)
        encoded = self.codec.encoder(input['img']*2-1,input['label'],protocol)
        output['compression']['code'] = self.codec.quantizer(encoded)
        if(protocol['tuning_param']['compression'] > 0):
            decoded = self.codec.decoder(output['compression']['code'],protocol)
            decoded = (decoded+1)/2
            output['compression']['img'] = decoded
            compression_loss = self.codec.compression_loss_fn(input,output,protocol)           
        
        classification_loss = torch.tensor(0,device=device,dtype=torch.float32)        
        if(protocol['tuning_param']['classification'] > 0):
            logit = self.classifier(output['compression']['code'],protocol)
            output['classification'] = logit
            classification_loss = self.classifier.classification_loss_fn(input,output,protocol) 
            
        output['loss'] = protocol['tuning_param']['compression']*compression_loss + protocol['tuning_param']['classification']*classification_loss
        return output          
    
    