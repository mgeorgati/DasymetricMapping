from tokenize import group
import numpy as np, random
from sklearn.feature_extraction.image import extract_patches_2d
from tensorflow.keras.models import *
from tensorflow.keras.layers import *
from tensorflow.keras.losses import *
from tensorflow.keras.backend import *
from tensorflow.keras import optimizers
from tensorflow.keras.initializers import *
from tensorflow.keras import activations
from mainFunctions import test_type
from itertools import product
from models import robustLoss as aloss
import itertools
from tensorflow.keras import backend as K
import tensorflow as tf

SEED = 42


def custom_activation(x):
    return K.elu(x)

####### THIS IS THE NEW CUSTOM LOSS FUNCTION FOR CNN
def averagepreds(y_pred):
    i = tf.constant(0)
    y_pred = tf.while_loop(tf.less(i, len(y_pred[0][-1])), averageinst(y_pred, i)) # Does this work?
    return y_pred[0]

def averageinst(y_pred):
    print('----IN AVERAGE')
    y = tf.split(y_pred, 2, axis =3)
    aver_pred = tf.keras.layers.Average()([y[0], y[1]])
    test_type(aver_pred)
    #y_pred[0] = tf.math.add(y_pred[0][:,:,:,:], y_pred[1][:,:,:,:])
    #y_pred[0] = tf.math.divide(y_pred[0], tf.cast(2, tf.float32))

    return aver_pred

def custom_loss_fn(group_split, nmodelpred = 1, reduce=True):
    def cl1(y_true, y_pred):
        
        #y_pred_final = tf.cond(tf.math.equal(nmodelpred, 2), averageinst(y_pred), y_pred)
        if nmodelpred == 2: 
            y_pred_final = averageinst(y_pred)
            y_pred = y_pred_final
        else: 
            y_pred_final = y_pred
        
        print('------ IN CLF----')
        numfinite = tf.math.count_nonzero(tf.math.is_finite(y_true[:,:,:,0]))
        mask = tf.where(tf.math.is_nan(y_true), K.constant(0.0), K.constant(1.0))
        y_true = tf.math.multiply_no_nan(y_true, mask)
        y_pred = tf.math.multiply_no_nan(y_pred, mask)
        #y_pred = tf.where(tf.math.is_nan(y_pred), K.constant(0), y_pred)
        
        if len(group_split) == 2 :
            # Custom loss sub-groups
            sumtrueg1 = tf.math.reduce_sum(y_true[:, :, :, 0:group_split[0]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumpredg1 = tf.math.reduce_sum(y_pred[:, :, :, 0:group_split[0]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumtrueg2 = tf.math.reduce_sum(y_true[:, :, :, group_split[0]:group_split[1]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumpredg2 = tf.math.reduce_sum(y_pred[:, :, :, group_split[0]:group_split[1]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            
            ##### none
            loss1 = tf.keras.metrics.mean_absolute_error(sumtrueg1, sumpredg1)
            loss2 = tf.keras.metrics.mean_absolute_error(sumtrueg2, sumpredg2)
            loss3 = tf.keras.metrics.mean_squared_error(y_true, y_pred_final)

            ##### _1
            #loss1 = tf.keras.metrics.mean_squared_error(sumtrueg1, sumpredg1)
            #loss2 = tf.keras.metrics.mean_squared_error(sumtrueg2, sumpredg2)
            #loss3 = tf.keras.metrics.mean_squared_error(y_true, y_pred_final)

            ##### _2
            #loss1 = tf.keras.metrics.mean_absolute_error(sumtrueg1, sumpredg1)
            #loss2 = tf.keras.metrics.mean_absolute_error(sumtrueg2, sumpredg2)
            #loss3 = tf.keras.metrics.mean_absolute_error(y_true, y_pred_final)

            loss = loss1 + loss2 + loss3
        elif len(group_split) == 3 :
                # Custom loss sub-groups
            sumtrueg1 = tf.math.reduce_sum(y_true[:, :, :, 0:group_split[0]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumpredg1 = tf.math.reduce_sum(y_pred[:, :, :, 0:group_split[0]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumtrueg2 = tf.math.reduce_sum(y_true[:, :, :, group_split[0]:group_split[1]+1], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumpredg2 = tf.math.reduce_sum(y_pred[:, :, :, group_split[0]:group_split[1]+1], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumtrueg3 = tf.math.reduce_sum(y_true[:, :, :, group_split[1]:group_split[2]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            sumpredg3 = tf.math.reduce_sum(y_pred[:, :, :, group_split[1]:group_split[2]], axis=3, keepdims=True)#, axis=3, keepdims=True)
            ##### none
            loss1 = tf.keras.metrics.mean_absolute_error(sumtrueg1, sumpredg1)
            loss2 = tf.keras.metrics.mean_absolute_error(sumtrueg2, sumpredg2)
            loss3 = tf.keras.metrics.mean_absolute_error(sumtrueg3, sumpredg3)
            loss4 = tf.keras.metrics.mean_squared_error(y_true, y_pred_final)

            loss = loss1 + loss2 + loss3 + loss4

        # The function tf.keras.metrics.mean_squared_error produced a result with shape = [batch_size, d0, .. dN-1].
        # Do you want that behaviour? Ou do you want to reduce already here the loss function to a single value?
        if reduce: loss = tf.math.divide_no_nan( tf.math.reduce_sum(loss) , tf.cast(numfinite, tf.float32) )
        return loss
    return cl1
#######

def smoothL1(hubervalue = 0.5, stdivalue = 0.01, nmodelpred=1):
    def sl1(y_true, y_pred):
        if nmodelpred == 2: 
            y_pred = averageinst(y_pred)
        else: 
            y_pred = y_pred
        
        numfinite = tf.math.count_nonzero(tf.math.is_finite(y_true))
        mask = tf.where(tf.math.is_nan(y_true), K.constant(0), K.constant(1))
        y_true = tf.math.multiply_no_nan(y_true, mask)
        y_pred = tf.math.multiply_no_nan(y_pred, mask)
        y_pred = tf.where(tf.math.is_nan(y_pred), K.constant(0), y_pred)

        # # RMSE
        rmse = K.sqrt(K.mean(K.square(y_pred - y_true)))
        return tf.math.divide_no_nan(rmse, tf.cast(numfinite, tf.float32))
    return sl1

def smoothLC1(hubervalue = 0.5, stdivalue = 0.01):
    def sl1(y_true, y_pred):
        numfinite = tf.math.count_nonzero(tf.math.is_finite(y_true))
        mask = tf.where(tf.math.is_nan(y_true), K.constant(0), K.constant(1))
        y_true = tf.math.multiply_no_nan(y_true, mask)
        y_pred = tf.math.multiply_no_nan(y_pred, mask)
        y_pred = tf.where(tf.math.is_nan(y_pred), K.constant(0), y_pred)

        # Version 2
        HUBER_DELTA = hubervalue
        y_pred_avg_two_channels = K.expand_dims(K.mean(y_pred, axis=-1), -1)
        x1 = K.abs(y_true - y_pred_avg_two_channels)
        x1 = tf.where(x1 < HUBER_DELTA, 0.5 * x1 ** 2, HUBER_DELTA * (x1 - 0.5 * HUBER_DELTA))
        x2 = K.abs(y_pred[:, :, :, 0] - y_pred[:, :, :, 1])
        x2 = tf.where(x2 < HUBER_DELTA, 0.5 * x2 ** 2, HUBER_DELTA * (x2 - 0.5 * HUBER_DELTA))
        sl = K.sum(x1) + K.sum(x2) + (10000*1/(1+tf.keras.backend.std(y_pred_avg_two_channels)))
        
        return tf.math.divide_no_nan(sl, tf.cast(numfinite, tf.float32))
    return sl1


def smoothLC1Adapt(aux_l1,aux_l2, aux_l3, aux_l4,aux_l5, aux_l6, aux_l7,aux_l8, aux_l9, aux_l10, 
            aux_l11, aux_l12, aux_l13, aux_l14, nmodelpred, nsubgroups=[5,12]):
    def slc1adapt(y_true, y_pred):

        if nmodelpred == 2: 
            y_pred_final = averageinst(y_pred)
            y_pred = y_pred_final
        else: 
            y_pred = y_pred

        numfinite = tf.math.count_nonzero(tf.math.is_finite(y_true))
        mask = tf.where(tf.math.is_nan(y_true), K.constant(0), K.constant(1))
        y_true = tf.math.multiply_no_nan(y_true, mask)
        y_pred = tf.math.multiply_no_nan(y_pred, mask)
        y_pred = tf.where(tf.math.is_nan(y_pred), K.constant(0), y_pred)
        
        # Custom loss sub-groups
        sumtrueg1 = tf.math.reduce_sum(y_true[:, :, :, 0:nsubgroups[0]], axis=3, keepdims=True)
        sumpredg1 = tf.math.reduce_sum(y_pred[:, :, :, 0:nsubgroups[0]], axis=3, keepdims=True)
        sumtrueg2 = tf.math.reduce_sum(y_true[:, :, :, nsubgroups[0]:nsubgroups[1]], axis=3, keepdims=True)
        sumpredg2 = tf.math.reduce_sum(y_pred[:, :, :, nsubgroups[0]:nsubgroups[1]], axis=3, keepdims=True)

        x1 = aux_l1(sumtrueg1 - sumpredg1)
        loss1 = tf.math.divide_no_nan(K.sum(x1), tf.cast(numfinite, tf.float32))
        x2 = aux_l2(sumtrueg2 - sumpredg2)
        loss2 = tf.math.divide_no_nan(K.sum(x2), tf.cast(numfinite, tf.float32))
        print('----IN RBLF----')
        
        # DIFFERENCE BETWEEN PRED AND TRUE
        x3 = aux_l3(y_true[:, :, :, 0] - y_pred[:, :, :, 0])
        print(x3)
        loss3 = tf.math.divide_no_nan(K.sum(x3), tf.cast(numfinite, tf.float32))
        print('---',loss3)
        x4 = aux_l4(y_true[:, :, :, 1] - y_pred[:, :, :, 1])
        loss4 = tf.math.divide_no_nan(K.sum(x4), tf.cast(numfinite, tf.float32))
        x5 = aux_l5(y_true[:, :, :, 2] - y_pred[:, :, :, 2])
        loss5 = tf.math.divide_no_nan(K.sum(x5), tf.cast(numfinite, tf.float32))
        x6 = aux_l6(y_true[:, :, :, 3] - y_pred[:, :, :, 3])
        loss6 = tf.math.divide_no_nan(K.sum(x6), tf.cast(numfinite, tf.float32))
        x7 = aux_l7(y_true[:, :, :, 4] - y_pred[:, :, :, 4])
        loss7 = tf.math.divide_no_nan(K.sum(x7), tf.cast(numfinite, tf.float32))
        x8 = aux_l8(y_true[:, :, :, 5] - y_pred[:, :, :, 5])
        loss8 = tf.math.divide_no_nan(K.sum(x8), tf.cast(numfinite, tf.float32))
        x9 = aux_l9(y_true[:, :, :, 6] - y_pred[:, :, :, 6])
        loss9 = tf.math.divide_no_nan(K.sum(x9), tf.cast(numfinite, tf.float32))
        x10 = aux_l10(y_true[:, :, :, 7] - y_pred[:, :, :, 7])
        loss10 = tf.math.divide_no_nan(K.sum(x10), tf.cast(numfinite, tf.float32))
        x11 = aux_l11(y_true[:, :, :, 8] - y_pred[:, :, :, 8])
        loss11 = tf.math.divide_no_nan(K.sum(x11), tf.cast(numfinite, tf.float32))
        x12 = aux_l12(y_true[:, :, :, 9] - y_pred[:, :, :, 9])
        loss12 = tf.math.divide_no_nan(K.sum(x12), tf.cast(numfinite, tf.float32))
        x13 = aux_l13(y_true[:, :, :, 10] - y_pred[:, :, :, 10])
        loss13 = tf.math.divide_no_nan(K.sum(x13), tf.cast(numfinite, tf.float32))
        x14 = aux_l14(y_true[:, :, :, 11] - y_pred[:, :, :, 11])
        loss14 = tf.math.divide_no_nan(K.sum(x14), tf.cast(numfinite, tf.float32))
        
        sl = loss1 + loss2 + loss3 + loss4 + loss5 + loss6 + loss7 + loss8 + loss9 + loss10 + loss11 + loss12 + loss13 + loss14 
        return sl
    return slc1adapt

class CustomModelAdaptive(tf.keras.Model):
    def __init__(self, inputs, outputs):
        super(CustomModelAdaptive, self).__init__(inputs, outputs)
        self.aux_l1 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l2 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l3 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l4 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l5 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l6 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l7 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l8 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l9 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l10 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l11 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l12 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l13 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.aux_l14 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
        self.sladapt = smoothLC1Adapt(self.aux_l1, self.aux_l2, self.aux_l3, self.aux_l4, self.aux_l5, self.aux_l6, 
                self.aux_l7, self.aux_l8, self.aux_l9, self.aux_l10, self.aux_l11, self.aux_l12, self.aux_l13, self.aux_l14, nmodelpred=2)
    
    def train_step(self, data):
        # Unpack the data. Its structure depends on your model and
        # on what you pass to `fit()`.
        x, y = data
        with tf.GradientTape(persistent=True) as tape:
            y_pred = self(x, training=True)  # Forward pass

            # Compute the loss value
            # (the loss function is configured in `compile()`)
            loss = self.compiled_loss(y, y_pred, regularization_losses=self.losses) # Must do
            loss = self.sladapt(y, y_pred)

        tf.print(loss)

        # Compute gradients
        model_vars = self.trainable_variables
        loss_vars = tf.unstack(self.aux_l1.trainable_variables + self.aux_l2.trainable_variables + self.aux_l3.trainable_variables 
                        + self.aux_l4.trainable_variables + self.aux_l5.trainable_variables + self.aux_l6.trainable_variables
                        + self.aux_l7.trainable_variables + self.aux_l8.trainable_variables + self.aux_l9.trainable_variables
                        + self.aux_l10.trainable_variables + self.aux_l11.trainable_variables + self.aux_l12.trainable_variables
                        + self.aux_l13.trainable_variables + self.aux_l14.trainable_variables)
        trainable_vars = list(model_vars) + list(loss_vars)
        gradients = tape.gradient(loss, trainable_vars)

        # Update weights
        self.optimizer.apply_gradients(zip(gradients, trainable_vars))

        # Update metrics (includes the metric that tracks the loss)
        self.compiled_metrics.update_state(y, y_pred)

        # Return a dict mapping metric names to current value
        return {m.name: m.result() for m in self.metrics}

def unet(inputs, attr_value, filters=[2,4,8,16,32], dropout=0.5):
    conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(inputs)
    # conv1 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(inputs)  # ALTERADO
    # conv1 = BatchNormalization()(conv1)  # ALTERADO
    # conv1 = Activation('relu')(conv1)  # ALTERADO

    conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv1)
    # conv1 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv1)  # ALTERADO
    # conv1 = BatchNormalization()(conv1)  # ALTERADO
    # conv1 = Activation('relu')(conv1)  # ALTERADO

    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool1)
    # conv2 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(pool1)  # ALTERADO
    # conv2 = BatchNormalization()(conv2)  # ALTERADO
    # conv2 = Activation('relu')(conv2)  # ALTERADO

    conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer ='he_normal')(conv2)
    # conv2 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv2)  # ALTERADO
    # conv2 = BatchNormalization()(conv2)  # ALTERADO
    # conv2 = Activation('relu')(conv2)  # ALTERADO

    pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)

    conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool2)
    # conv3 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(pool2)  # ALTERADO
    # conv3 = BatchNormalization()(conv3)  # ALTERADO
    # conv3 = Activation('relu')(conv3)  # ALTERADO

    conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv3)
    # conv3 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv3)  # ALTERADO
    # conv3 = BatchNormalization()(conv3)  # ALTERADO
    # conv3 = Activation('relu')(conv3)  # ALTERADO

    pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)

    conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool3)
    # conv4 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(pool3)  # ALTERADO
    # conv4 = BatchNormalization()(conv4)  # ALTERADO
    # conv4 = Activation('relu')(conv4)  # ALTERADO

    conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv4)
    # conv4 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv4)  # ALTERADO
    # conv4 = BatchNormalization()(conv4)  # ALTERADO
    # conv4 = Activation('relu')(conv4)  # ALTERADO

    drop4 = Dropout(dropout)(conv4)
    pool4 = MaxPooling2D(pool_size=(2, 2))(drop4)

    conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool4)
    # conv5 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(pool4)  # ALTERADO
    # conv5 = BatchNormalization()(conv5)  # ALTERADO
    # conv5 = Activation('relu')(conv5)  # ALTERADO

    conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv5)
    # conv5 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv5)  # ALTERADO
    # conv5 = BatchNormalization()(conv5)  # ALTERADO
    # conv5 = Activation('relu')(conv5)  # ALTERADO

    drop5 = Dropout(dropout)(conv5)

    up6 = Conv2D(filters[3], 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        UpSampling2D(size=(2, 2))(drop5))
    merge6 = concatenate([drop4, up6], axis=3)

    conv6 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge6)
    # conv6 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(merge6)  # ALTERADO
    # conv6 = BatchNormalization()(conv6)  # ALTERADO
    # conv6 = Activation('relu')(conv6)  # ALTERADO

    conv6 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv6)
    # conv6 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv6)  # ALTERADO
    # conv6 = BatchNormalization()(conv6)  # ALTERADO
    # conv6 = Activation('relu')(conv6)  # ALTERADO

    up7 = Conv2D(filters[2], 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        UpSampling2D(size=(2, 2))(conv6))
    merge7 = concatenate([conv3, up7], axis=3)

    conv7 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge7)
    # conv7 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(merge7)  # ALTERADO
    # conv7 = BatchNormalization()(conv7)  # ALTERADO
    # conv7 = Activation('relu')(conv7)  # ALTERADO

    conv7 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv7)
    # conv7 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv7)  # ALTERADO
    # conv7 = BatchNormalization()(conv7)  # ALTERADO
    # conv7 = Activation('relu')(conv7)  # ALTERADO

    up8 = Conv2D(filters[1], 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        UpSampling2D(size=(2, 2))(conv7))
    merge8 = concatenate([conv2, up8], axis=3)

    conv8 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge8)
    # conv8 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(merge8)  # ALTERADO
    # conv8 = BatchNormalization()(conv8)  # ALTERADO
    # conv8 = Activation('relu')(conv8)  # ALTERADO

    conv8 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv8)
    # conv8 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv8)  # ALTERADO
    # conv8 = BatchNormalization()(conv8)  # ALTERADO
    # conv8 = Activation('relu')(conv8)  # ALTERADO

    up9 = Conv2D(filters[0], 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        UpSampling2D(size=(2, 2))(conv8))
    merge9 = concatenate([conv1, up9], axis=3)

    conv9 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge9)
    # conv9 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(merge9)  # ALTERADO
    # conv9 = BatchNormalization()(conv9)  # ALTERADO
    # conv9 = Activation('relu')(conv9)  # ALTERADO

    conv9 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)
    # conv9 = Conv2D(filters[0], 3, padding='same', kernel_initializer='he_normal')(conv9)  # ALTERADO
    # conv9 = BatchNormalization()(conv9)  # ALTERADO
    # conv9 = Activation('relu')(conv9)  # ALTERADO
    
    # New
    aux = concatenate([conv9, inputs], axis=3)
    # aux = conv9
    print("in UNET: conv9", conv9.shape, "aux:", aux.shape)
    output = Conv2D(len(attr_value), 1, activation='linear')(aux) # CHANGED: Conv2D(1, 1, activation='linear')(aux)
    print("output of unet:", output.shape)
    return output


def compilecnnmodel(cnnmod, attr_value, group_split, shape, lrate, loss_function, useFlippedImages, dropout=0.5, filters=[2,4,8,16,32], lweights=[1/2, 1/2],
                    hubervalue=0.5, stdivalue=0.01):
    tf.random.set_seed(SEED)

    if cnnmod == 'cnnlm':
        shape = [7]
        mod = Sequential()
        mod.add(Dense(units=1, input_shape=shape))
        mod.add(Activation('linear'))
        mod.compile(loss='mean_squared_error', optimizer=optimizers.Adam(lr=lrate))

    elif cnnmod == 'lenet':
        mod = Sequential()
        mod.add(Conv2D(filters=filters[0], kernel_size=3, padding='same', input_shape=shape, activation='relu'))
        mod.add(MaxPooling2D(pool_size=(2, 2)))
        mod.add(Conv2D(filters=filters[1], kernel_size=3, padding='same'))
        mod.add(Activation('relu'))
        mod.add(MaxPooling2D(pool_size=(2, 2)))
        mod.add(Dropout(rate=0.1))
        mod.add(Flatten())
        mod.add(Dense(units=filters[2]))
        mod.add(Activation('relu'))
        mod.add(Dense(units=1))
        mod.add(Activation('linear'))
        mod.compile(loss='mean_squared_error', optimizer=optimizers.Adam(lr=lrate))

    elif cnnmod == 'vgg':
        mod = Sequential()
        mod.add(Conv2D(filters[0], 3, activation='relu', padding='same', input_shape=shape, name='block1_conv1'))
        mod.add(Conv2D(filters[0], 3, activation='relu', padding='same', name='block1_conv2'))
        mod.add(MaxPooling2D((2, 2), strides=(2, 2), name='block1_pool'))
        mod.add(Conv2D(filters[1], 3, activation='relu', padding='same', name='block2_conv1'))
        mod.add(Conv2D(filters[1], 3, activation='relu', padding='same', name='block2_conv2'))
        mod.add(MaxPooling2D((2, 2), strides=(2, 2), name='block2_pool'))
        mod.add(Conv2D(filters[2], 3, activation='relu', padding='same', name='block3_conv1'))
        mod.add(Conv2D(filters[2], 3, activation='relu', padding='same', name='block3_conv2'))
        mod.add(Conv2D(filters[2], 3, activation='relu', padding='same', name='block3_conv3'))
        mod.add(MaxPooling2D((2, 2), strides=(2, 2), name='block3_pool'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block4_conv1'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block4_conv2'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block4_conv3'))
        mod.add(MaxPooling2D((2, 2), strides=(2, 2), name='block4_pool'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block5_conv1'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block5_conv2'))
        mod.add(Conv2D(filters[3], 3, activation='relu', padding='same', name='block5_conv3'))
        mod.add(MaxPooling2D((2, 2), strides=(2, 2), name='block5_pool'))
        mod.add(Flatten(name='flatten'))
        mod.add(Dense(filters[4], activation='relu', name='fc1'))
        mod.add(Dense(filters[4], activation='relu', name='fc2'))
        mod.add(Dense(units=1, activation='linear', name='predictions'))
        mod.compile(loss='mean_squared_error', optimizer=optimizers.Adam(lr=lrate))

    elif cnnmod == 'uenc':
        inputs = Input(shape)
        conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(inputs)
        conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv1)
        pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)
        conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool1)
        conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv2)
        pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)
        conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool2)
        conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv3)
        pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)
        conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool3)
        conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv4)
        drop4 = Dropout(0.5)(conv4)
        pool4 = MaxPooling2D(pool_size=(2, 2))(drop4)
        conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool4)
        conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv5)
        drop5 = Dropout(0.5)(conv5)
        flat1 = Flatten()(drop5)
        dens1 = Dense(units=1, activation='linear', name='predictions')(flat1)
        mod = Model(inputs=inputs, outputs=dens1)
        mod.compile(loss='mean_squared_error', optimizer=optimizers.Adam(lr=lrate))

    elif cnnmod == 'unet':
        if useFlippedImages == 'yes':
            print('| --- Unet - Data augmentation with random method')
            inputs = Input(shape)
            
            # # Random transformation to apply
            randomint = K.constant(random.randint(0, 5))
            #
            def t0(inputs): return Lambda(lambda x: K.reverse(x, axes=1))(inputs) # Horizontal flip
            def t1(inputs): return Lambda(lambda x: K.reverse(x, axes=2))(inputs) # Vertical flip
            def t2(inputs): return Lambda(lambda x: K.reverse(x, axes=(1,2)))(inputs) # Horizontal and vertical flip
            def t3(inputs): return Lambda(lambda x: K.permute_dimensions(x, [0, 2, 1, 3]))(inputs) # Transpose
            def t4(inputs): return Lambda(lambda x: K.reverse(t3(x), axes=1))(inputs) # Rotate clockwise
            def t5(inputs): return Lambda(lambda x: K.reverse(t3(x), axes=2))(inputs) # Rotate counter clockwise
            
            input_b = tf.case([(tf.equal(randomint, K.constant(0)), lambda: t0(inputs)),
                                (tf.equal(randomint, K.constant(1)), lambda: t1(inputs)),
                                (tf.equal(randomint, K.constant(2)), lambda: t2(inputs)),
                                (tf.equal(randomint, K.constant(3)), lambda: t3(inputs)),
                                (tf.equal(randomint, K.constant(4)), lambda: t4(inputs)),
                                (tf.equal(randomint, K.constant(5)), lambda: t5(inputs))],
                            exclusive=True)
            
            # # Contrastive
            input_b = Lambda(lambda x: K.permute_dimensions(x, [0, 2, 1, 3]))(inputs)
            processed_a = unet(inputs, attr_value, filters, dropout)
            
            processed_b = unet(input_b, attr_value, filters, dropout)
            processed_b = Lambda(lambda x: K.permute_dimensions(x, [0, 2, 1, 3]))(processed_b)
            
            processed_b = tf.case([(tf.equal(randomint, K.constant(0)), lambda: t0(processed_b)),
                                    (tf.equal(randomint, K.constant(1)), lambda: t1(processed_b)),
                                    (tf.equal(randomint, K.constant(2)), lambda: t2(processed_b)),
                                    (tf.equal(randomint, K.constant(3)), lambda: t3(processed_b)),
                                    (tf.equal(randomint, K.constant(4)), lambda: t5(processed_b)),
                                    (tf.equal(randomint, K.constant(5)), lambda: t4(processed_b))],
                                exclusive=True)

            # THIS IS FOR CONCATENATING THE FLIPPING IMAGES
            # The result is a tensor of shape: (None, 16, 16, 24)
            result = Concatenate()([processed_a, processed_b])
            
            #SELECT LOSS FUNCTION
            if loss_function == 'clf':
                mod = Model(inputs=inputs, outputs=result)
                # CUSTOM LOSS
                sl1 = custom_loss_fn(group_split, nmodelpred = 2, reduce=True) #= [5, 12]
                mod.compile(loss=sl1, optimizer=optimizers.Adam(lr=lrate))
            elif loss_function == 'rblf':
                aux_l1 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l2 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l3 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l4 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l5 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l6 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l7 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l8 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l9 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l10 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l11 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l12 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l13 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l14 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                mod = CustomModelAdaptive(inputs=inputs, outputs=result) # CustomModel
                # Robust Loss Function
                print('THIS FUNCTION NEEDS TO BE FIXED')
                sl1 = smoothLC1Adapt(aux_l1, aux_l2, aux_l3, aux_l4, aux_l5, aux_l6, aux_l7, aux_l8,aux_l9, aux_l10, aux_l11, aux_l12, aux_l13, aux_l14,nmodelpred=2 )
                mod.compile(loss= sl1, optimizer=optimizers.Adam(lr=lrate), run_eagerly=False)
            elif loss_function == 'rmse':
                mod = Model(inputs=inputs, outputs=result)
                # RMSE
                sl1 = smoothL1(hubervalue=hubervalue, stdivalue=stdivalue, nmodelpred=2)
                mod.compile(loss=sl1, optimizer=optimizers.Adam(lr=lrate))
        
        else:
            
            inputs = Input(shape)
            print('| --- Unet - Using only the input layers, no augmentation')

            result = unet(inputs, attr_value, filters, dropout)
            
            #SELECT LOSS FUNCTION
            if loss_function == 'clf':
                mod = Model(inputs=inputs, outputs=result) # CustomModel
                # CUSTOM LOSS
                sl1 = custom_loss_fn(group_split, nmodelpred = 1, reduce=True) #nsubgroups = [5, 12]
                mod.compile(loss=sl1, optimizer=optimizers.Adam(lr=lrate))
            elif loss_function == 'rblf':
                aux_l1 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l2 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l3 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l4 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l5 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l6 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l7 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l8 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l9 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l10 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l11 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l12 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l13 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                aux_l14 = aloss.AdaptiveLossFunction(num_channels=1, float_dtype=np.float32)
                mod = CustomModelAdaptive(inputs=inputs, outputs=result) # CustomModel
                # Robust Loss Function
                print('THIS FUNCTION NEEDS TO BE FIXED')
                sl1 = smoothLC1Adapt(aux_l1, aux_l2, aux_l3, aux_l4, aux_l5, aux_l6, aux_l7, aux_l8,aux_l9, aux_l10, aux_l11, aux_l12, aux_l13, aux_l14,nmodelpred )
                mod.compile(loss= sl1, optimizer=optimizers.Adam(lr=lrate), run_eagerly=False)
            elif loss_function == 'rmse':
                mod = Model(inputs=inputs, outputs=result) # CustomModel
                # RMSE
                sl1 = smoothL1(hubervalue=hubervalue, stdivalue=stdivalue, nmodelpred=1)
                mod.compile(loss=sl1, optimizer=optimizers.Adam(lr=lrate))
            
            # HUBER LOSS
            #sl1 = smoothLC1(hubervalue=hubervalue, stdivalue=stdivalue)
            
             #run_eagerly=False (test if error)

    elif cnnmod == '2runet':
        inputs = Input(shape)
        conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(inputs)
        conv1 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv1)
        pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)
        conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool1)
        conv2 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv2)
        pool2 = MaxPooling2D(pool_size=(2, 2))(conv2)
        conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool2)
        conv3 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv3)
        pool3 = MaxPooling2D(pool_size=(2, 2))(conv3)
        conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool3)
        conv4 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv4)
        drop4 = Dropout(0.5)(conv4)
        pool4 = MaxPooling2D(pool_size=(2, 2))(drop4)

        conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(pool4)
        conv5 = Conv2D(filters[4], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv5)
        drop5 = Dropout(0.5)(conv5)

        up6 = Conv2D(filters[3], 2, activation='relu', padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(drop5))
        merge6 = concatenate([drop4, up6], axis=3)
        conv6 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge6)
        conv6 = Conv2D(filters[3], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv6)

        up7 = Conv2D(filters[2], 2, activation='relu', padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(conv6))
        merge7 = concatenate([conv3, up7], axis=3)
        conv7 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge7)
        conv7 = Conv2D(filters[2], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv7)

        up8 = Conv2D(filters[1], 2, activation='relu', padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(conv7))
        merge8 = concatenate([conv2, up8], axis=3)
        conv8 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge8)
        conv8 = Conv2D(filters[1], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv8)

        up9 = Conv2D(filters[0], 2, activation='relu', padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(conv8))
        merge9 = concatenate([conv1, up9], axis=3)
        conv9 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge9)
        conv9 = Conv2D(filters[0], 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)


        # High resolution output
        outputhr = Conv2D(1, 1, activation='linear', name="highres")(conv9)

        # Sum of high resolution output
        avgpoolinghr = AveragePooling2D(pool_size=4)(outputhr)
        outputlr = Lambda(lambda x: x * 4, name="lowres")(avgpoolinghr)

        mod = Model(inputs=inputs, outputs=[outputhr, outputlr])
        mod.compile(loss=['mean_squared_error', 'mean_squared_error'],
                    loss_weights=lweights,
                    optimizer=optimizers.Adam(lr=lrate))

    return mod

def createpatches(X, city, ROOT_DIR, patchsize, padding, stride=1, cstudy=None):
    if cstudy:
        try:
            fp = np.memmap(ROOT_DIR + "/Temp/{}/".format(city) + cstudy + '.dat', mode='r')
            print('Found .dat file')
            ninstances = int(fp.shape[0] / patchsize / patchsize / X.shape[2] / 4) # Divide by dimensions
            shapemmap = (ninstances, patchsize, patchsize, X.shape[2])
            fp = np.memmap(cstudy + '.dat', dtype='float32', mode='r', shape=shapemmap)
        except:
            print('Did not find .dat file')
            if padding:
                rowpad = int((patchsize - 1) / 2)
                colpad = int(round((patchsize - 1) / 2))
                newX = np.pad(X, ((rowpad, colpad), (rowpad, colpad), (0, 0)), 'constant', constant_values=(0, 0))
            else:
                newX = X
            newX[np.isnan(newX)] = -9999999
            patches = extract_patches_2d(newX, [16, 16])
            patches[patches == -9999999] = np.nan
            fp = np.memmap(ROOT_DIR + "/Temp/{}/".format(city) + cstudy + '.dat', dtype='float32', mode='w+', shape=patches.shape)
            fp[:] = patches[:]
            fp = fp.reshape(-1, patchsize, patchsize, X.shape[2])
        print("fp in ku:", fp.shape)
        return fp
    else:
        if padding:
            rowpad = int((patchsize - 1) / 2)
            colpad = int(round((patchsize - 1) / 2))
            newX = np.pad(X, ((rowpad, colpad), (rowpad, colpad), (0, 0)), 'constant', constant_values=(0, 0))
        else:
            newX = X

        newX[np.isnan(newX)] = -9999999
        patches = extract_patches_2d(newX, [16, 16])
        patches[patches == -9999999] = np.nan
        patches = patches.reshape(-1, patchsize, patchsize, X.shape[2])
        print("patches in ku:", patches.shape)
        return patches

def reconstructpatches(patches, image_size, stride):    
    #if len(patches.shape) == 4:
        #aux = [ reconstructpatches(patches[:,:,:,a], image_size, stride) for a in range(patches.shape[3]) ]
        #return np.moveaxis( np.array(aux), 0, 2)
    i_h, i_w = image_size[:2]
    p_h, p_w = patches.shape[1:3]
    mean = np.zeros(image_size)
    patch_count = np.zeros(image_size)
    n_h = int((i_h - p_h) / stride + 1)
    n_w = int((i_w - p_w) / stride + 1)
    for p, (i, j) in zip(patches, itertools.product(range(n_h), range(n_w))):
        patch_count[i * stride:i * stride + p_h, j * stride:j * stride + p_w] += ~np.isnan(p)
        ctignore = np.isnan(p)
        p[ctignore] = 0
        mean[i * stride:i * stride + p_h, j * stride:j * stride + p_w] += p
        p[ctignore] = np.nan
    mean = np.divide(mean, patch_count, out=np.zeros_like(mean), where=patch_count != 0)
    return mean


