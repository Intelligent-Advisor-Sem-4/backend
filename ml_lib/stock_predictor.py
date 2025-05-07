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
from ml_lib.stock_market_handlerV2 import model_regiterer,get_model_details,store_prediction,get_all_available_companies



# def getStockData(company, starting_date=None, ending_date=None, size=None):
#     response = yf.Ticker(company).history(period='max', interval='1d')
#     if starting_date:
#         response = response.loc[response.index >= starting_date]
#     if ending_date:
#         response = response.loc[response.index <= ending_date]
#     if size:
#         return response.tail(size)
#     return response


def getStockData(company, starting_date=None, ending_date=None, size=None):
    response = yf.Ticker(company).history(period='max', interval='1d')
    print(response.tail())
    last_close_price = response['Close'].iloc[-1] if not response.empty else None
    next_last_close_price = response['Close'].iloc[-2] if len(response) > 1 else None
    perce = ((last_close_price-next_last_close_price)/next_last_close_price)*100
    if starting_date:
        response = response.loc[response.index >= starting_date]
    if ending_date:
        response = response.loc[response.index <= ending_date]
    if size:
        return response.tail(size)
    last_date = response.index[-1] if not response.empty else None
    return [response,last_close_price,perce,last_date]

def trainer(company_name,batch=32,input_dim=90,lc=128):
    stdata = getStockData(company_name)
    close_prices_b = stdata[0]['Close'].values
    scaler = MinMaxScaler()
    output_dim = 7
    close_prices = scaler.fit_transform(close_prices_b.reshape(-1,1))
    try:

        X, Y = [], []
        for i in range(len(close_prices) - input_dim-output_dim):
            X.append(close_prices[i:i+input_dim])
            Y.append(close_prices[i+input_dim:i+input_dim+output_dim])

        X = np.array(X).reshape(-1, input_dim, 1)
        Y = np.array(Y)
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.05, shuffle=False)
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.LSTM(lc,input_shape=(input_dim, 1)))
        model.add(tf.keras.layers.Dense(output_dim))
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='mse')
        model.summary()
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='loss',patience=10,restore_best_weights=True,verbose=1)

        model.fit(X_train,Y_train,epochs=100,batch_size=batch,callbacks=[early_stop],verbose=1,validation_split=0.1)

        prediction = model.predict(X_test)
        final_rmse = math.sqrt(mean_squared_error(Y_test.flatten(), prediction.flatten()))
        prediction = scaler.inverse_transform(prediction.reshape(-1, 1)).reshape(prediction.shape)
        Y_test = scaler.inverse_transform(Y_test.reshape(-1, 1)).reshape(Y_test.shape)
        print(f"Final RMSE: {final_rmse:.5f}")
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
        #Generate graphs for predicted vs actual values for each index
        # for i in range(output_dim):
        #     plt.figure(figsize=(8, 5))
        #     plt.plot(range(len(Y_test)), Y_test[:, i], label=f"Actual Value (Index {i})", color="green", marker="x")
        #     plt.plot(range(len(prediction)), prediction[:, i], label=f"Predicted Value (Index {i})", color="blue", marker="o")
        #     plt.xlabel("Sample Index")
        #     plt.ylabel("Price")
        #     plt.title(f"Actual vs Predicted Values for Index {i}")
        #     plt.legend()
        #     plt.grid()
        #     plt.show()
        model_regiterer(company_name,time_step=90,rmse=final_rmse,model_location=model_path,scaler_location=scaler_file,last_date=stdata[-1])
        return model,final_rmse
    except Exception as err:
        print(f"An error occurred: {err}")

# data = yf.download(get_all_available_companies()[:25], group_by='ticker', period='max', threads=False)

# for i in get_all_available_companies()[:25]:
#     models_folder = "trainedModels"
#     model_path = os.path.join("ml_lib",models_folder, f"{i}_trained_model.keras")
#     if os.path.exists(model_path) and get_model_details(i)!=None:
#         print(f"Model for {i} already exists. Skipping training.")
#         continue
#     trainer(i)

# trainer('AAPL')


def predict(company_name, date):
    input_dim = 90
    print(company_name,date)
    model_detail = get_model_details(company_name)
    if model_detail == None:
        return None
    model_path = model_detail.model_location
    if not os.path.exists(model_path):
        print(f"Model file for {company_name} not found.")
        return None
    model = tf.keras.models.load_model(model_path)
    scaler_file = model_detail.scaler_location
    if not os.path.exists(scaler_file):
        print(f"Scaler file for {company_name} not found.")
        return None

    with open(scaler_file, "rb") as f:
        scaler = pickle.load(f)

        previous_data = getStockData(company_name,ending_date=date,size=input_dim)['Close']
        last_date = previous_data.index[-1].date()
        previous_data = previous_data.values
        print(last_date)


        previous_data = scaler.transform(previous_data.reshape(-1, 1)).reshape(1, input_dim, 1)

        prediction = model.predict(previous_data)
        prediction = scaler.inverse_transform(prediction.reshape(-1, 1)).flatten()
        output = {}
        print(len(prediction))
        if(model_detail.model_id!=None):
            print(model_detail.model_id)
            for i in range(len(prediction)):
                output[last_date+timedelta(days=i+1)]=float(prediction[i])
                store_prediction(model_id=model_detail.model_id,last_actual_date=last_date,predicted_date=last_date+timedelta(days=i+1),predicted_price=float(prediction[i]))
        return output




