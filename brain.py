from keras.models import load_model
import numpy as np

class Brain():
    '''handle all the sensor to actuator stuff here'''
    def __init__(self, feature_model=None, lstm_model=None, N=5):
        if feature_model:
            self.feature_net = load_model(feature_model)
        
        if lstm_model:
            self.lstm = load_model(lstm_model)
            
        self.N = N
        self.reset_memory()
        
        
    def reset_memory(self):
        self.feature_memory = [np.zeros(shape=(1,256)) for i in range(self.N)]

    def predict_theta(self,image):
        #pop a frame from the memory
        self.feature_memory.pop(0)
        image_feature = self.feature_net.predict(np.expand_dims(image,0))
        self.feature_memory.append(image_feature)
        
        #feed the lstm
        z = np.expand_dims( np.concatenate(self.feature_memory),0)
        theta = self.lstm.predict(z)[0][0]
        return theta