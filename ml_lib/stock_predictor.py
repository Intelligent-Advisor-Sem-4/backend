import yfinance as yf
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import math
import requests
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import pickle
from datetime import datetime, timedelta
from ml_lib.stock_market_handlerV2 import model_regiterer,get_model_details,store_prediction


def predict_with_uncertainty(model, input_data, scaler, n_iter=50):
    try:
        predictions = []
        for _ in range(n_iter):
            pred = model(input_data, training=True).numpy()
            predictions.append(pred)
        predictions = np.array(predictions)
        mean_pred = predictions.mean(axis=0).flatten()
        std_pred = predictions.std(axis=0).flatten()
        mean_pred = scaler.inverse_transform(mean_pred.reshape(-1, 1)).flatten()
        std_pred = (std_pred * scaler.data_range_[0]).flatten()
        return mean_pred, std_pred
    except Exception as e:
        print(f"Error in predict_with_uncertainty: {e}")
        return None, None


@tf.keras.utils.register_keras_serializable()
class LSTMWithDropout(tf.keras.Model):
    def __init__(self, units=128, output_dim=7, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.output_dim = output_dim
        self.lstm = tf.keras.layers.LSTM(units)
        self.dropout = tf.keras.layers.Dropout(0.2)
        self.dense = tf.keras.layers.Dense(output_dim)

    def call(self, inputs, training=False):
        x = self.lstm(inputs)
        x = self.dropout(x, training=training)
        return self.dense(x)

    def get_config(self):
        config = super().get_config()
        config.update({
            "units": self.units,
            "output_dim": self.output_dim
        })
        return config

    @classmethod
    def from_config(cls, config):
        return cls(**config)


def getStockData(company, starting_date=None, ending_date=None, size=None,size_dir = -1):
    try:
        response = yf.Ticker(company).history(period='max', interval='1d')
        # print(response.tail())
        last_close_price = response['Close'].iloc[-1] if not response.empty else None
        next_last_close_price = response['Close'].iloc[-2] if len(response) > 1 else None
        perce = ((last_close_price-next_last_close_price)/next_last_close_price)*100 if starting_date and ending_date else None
        if starting_date:
            response = response.loc[response.index >= starting_date]
        if ending_date:
            response = response.loc[response.index <= ending_date]
        if size and size_dir== 1:
            response = response.head(size)
        elif size:
            response = response.tail(size)
        last_date = response.index[-1] if not response.empty else None 
        print("point 3 pass")
        return [response,last_close_price,perce,last_date]
    except Exception as e:
        print(f"Error in getStockData: {e}")
        return None



def mean_absolute_percentage_error(y_true, y_pred): 
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def trainer(company_name,batch=32,input_dim=90,lc=128):
    try:
        stdata = getStockData(company_name)
        close_prices_b = stdata[0]['Close'].values
        scaler = MinMaxScaler()
        output_dim = 7
        close_prices = scaler.fit_transform(close_prices_b.reshape(-1,1))
        dataset_length = len(close_prices)
        print(f"Length of dataset: {dataset_length}")
        try:

            X, Y = [], []
            for i in range(len(close_prices) - input_dim-output_dim):
                X.append(close_prices[i:i+input_dim])
                Y.append(close_prices[i+input_dim:i+input_dim+output_dim])

            X = np.array(X).reshape(-1, input_dim, 1)
            Y = np.array(Y)
            X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.05, shuffle=False)
            model = LSTMWithDropout(lc, output_dim)
            model.compile(optimizer='adam', loss=tf.keras.losses.Huber())
            model.summary()
            early_stop = tf.keras.callbacks.EarlyStopping(monitor='loss',patience=10,restore_best_weights=True,verbose=1)

            model.fit(X_train,Y_train,epochs=100,batch_size=batch,callbacks=[early_stop],verbose=1)

            prediction = model.predict(X_test)
            final_rmse = math.sqrt(mean_squared_error(Y_test.flatten(), prediction.flatten()))
            prediction = scaler.inverse_transform(prediction.reshape(-1, 1)).reshape(prediction.shape)
            Y_test = scaler.inverse_transform(Y_test.reshape(-1, 1)).reshape(Y_test.shape)
            mape = mean_absolute_percentage_error(Y_test.flatten(), prediction.flatten())
            accuracy_percent = 100 - mape
            print("-------------------------------------------------------------------------------------")
            print(f"MAPE: {mape:.2f}%")
            print(f"Approximate Accuracy: {accuracy_percent:.2f}%")
            print(f"Final RMSE: {final_rmse:.5f}")
            print("---------------------------------------------------------------------------------------------")
            models_folder = "trainedModels"
            if not os.path.exists(os.path.join("ml_lib",models_folder)):
                os.makedirs(os.path.join("ml_lib",models_folder))

            scaler_file = os.path.join("ml_lib",models_folder, f"{company_name}_scaler.pkl")
            with open(scaler_file, "wb") as f:
                pickle.dump(scaler, f)
            print(f"Scaler saved as '{scaler_file}'")
            model_path = os.path.join("ml_lib",models_folder, f"{company_name}_trained_model.keras")
            model.save(model_path)
            print(f"Model saved as '{model_path}'")
            # images_folder = os.path.join("ml_lib", "images")
            # if not os.path.exists(images_folder):
            #     os.makedirs(images_folder)

            # for i in range(output_dim):
            #     plt.figure(figsize=(8, 5))
            #     plt.plot(range(len(Y_test)), Y_test[:, i], label=f"Actual Value (Index {i})", color="green", marker="x")
            #     plt.plot(range(len(prediction)), prediction[:, i], label=f"Predicted Value (Index {i})", color="blue", marker="o")
            #     plt.xlabel("Sample Index")
            #     plt.ylabel("Price")
            #     plt.title(f"Actual vs Predicted Values {i+1} st/nd/rd/th day")
            #     plt.legend()
            #     plt.grid()
            #     graph_path = os.path.join(images_folder, f"{company_name}_{i}_graph.png")
            #     plt.savefig(graph_path)
            #     plt.close()
            #     print(f"Graph saved as '{graph_path}'")
            model_regiterer(company_name,time_step=input_dim,rmse=final_rmse,model_location=model_path,scaler_location=scaler_file,last_date=stdata[-1],data_points=int(dataset_length-dataset_length*0.05))
            return model,final_rmse
        except Exception as err:
            print(f"An error occurred: {err}")
    except Exception as e:
        print(f"Error in trainer: {e}")
        return None, None


def predict(company_name, date):
    try:
        input_dim = 90
        # print(company_name,date)
        model_detail = get_model_details(company_name)
        if model_detail == None:
            print("no model details")
            return None
        model_path = os.path.join("ml_lib","trainedModels", f"{company_name}_trained_model.keras")
        if not os.path.exists(model_path):
            print(f"Model file for {company_name} not found.")
            return None
        model = tf.keras.models.load_model(model_path)
        scaler_file = os.path.join("ml_lib","trainedModels", f"{company_name}_scaler.pkl")
        if not os.path.exists(scaler_file):
            print(f"Scaler file for {company_name} not found.")
            return None

        with open(scaler_file, "rb") as f:
            scaler = pickle.load(f)

            previous_data = getStockData(company_name,ending_date=date,size=input_dim)[0]['Close']
            last_date = previous_data.index[-1].date()
            previous_data = previous_data.values
            # print(last_date)


            previous_data = scaler.transform(previous_data.reshape(-1, 1)).reshape(1, input_dim, 1)

            mean_prediction, std_prediction = predict_with_uncertainty(model, previous_data, scaler, n_iter=50)
            output = {}
            if model_detail.model_id is not None:
                for i in range(len(mean_prediction)):
                    predicted_date = last_date + timedelta(days=i + 1)
                    output[predicted_date] = {
                        "predicted_price": float(mean_prediction[i]),
                        "confidence_interval": float(std_prediction[i])
                    }
                    store_prediction(
                        model_id=model_detail.model_id,
                        last_actual_date=last_date,
                        predicted_date=predicted_date,
                        predicted_price=float(mean_prediction[i]),
                        confidencescore=float(std_prediction[i])
                    )
            print(std_prediction)
            print("=================================================================================================================")
            return output
    except Exception as e:
        print(f"Error in predict: {e}")
        return None





