import pandas as pd
import yfinance as yf
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from .stock_market_handlerV2 import get_all_available_companies,get_past_history,get_data,model_regiterer
import math
from sklearn.preprocessing import MinMaxScaler
import pickle



def trainerV2(company_name,batch=32,input_dim=90,lc=128):
    close_prices_c = get_data(company=company_name)
    # for k in close_prices_c[:20]:
    #     print(f"{k.price_date}        {k.close_price}")
    # # cl = get_past_history(company=company_name)['Close']
    # # print("")
    # # print(cl[:20])
    close_prices_b = np.array([float(i.close_price) for i in close_prices_c])
    scaler = MinMaxScaler()
    output_dim = 7
    close_prices_mean = np.mean(close_prices_b)
    close_prices_std = np.std(close_prices_b)
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
        model.add(tf.keras.layers.LSTM(lc, input_shape=(input_dim, 1)))
        # model.add(tf.keras.layers.Dropout(0.2))
        #model.add(tf.keras.layers.LSTM(128,return_sequences=True))
        # model.add(tf.keras.layers.Dropout(0.2))
        # model.add(tf.keras.layers.LSTM(128))
        # model.add(tf.keras.layers.Dropout(0.2))
        model.add(tf.keras.layers.Dense(output_dim))
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='mse')
        model.summary()
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='loss',patience=5,restore_best_weights=True,verbose=1)

        model.fit(X_train,Y_train,epochs=100,batch_size=batch,callbacks=[early_stop],verbose=1,validation_split=0.1)

        prediction = model.predict(X_test)
        final_rmse = math.sqrt(mean_squared_error(Y_test.flatten(), prediction.flatten()))
        prediction = scaler.inverse_transform(prediction.reshape(-1, 1)).reshape(prediction.shape)
        Y_test = scaler.inverse_transform(Y_test.reshape(-1, 1)).reshape(Y_test.shape)
        print(f"Final RMSE: {final_rmse:.5f}")
        models_folder = "trainedModels"
        if not os.path.exists(os.path.join("ml_lib",models_folder)):
            os.makedirs(os.path.join("ml_lib",models_folder))

        scaler_file = os.path.join("ml_lib","trainedModels", f"{company_name}_scaler.pkl")
        with open(scaler_file, "wb") as f:
            pickle.dump(scaler, f)
        print(f"Scaler saved as '{scaler_file}'")
        # print(f"Statistics saved as '{stats_file}'")
        model_path = os.path.join("ml_lib","trainedModels", f"{company_name}_trained_model.keras")
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
        return model,final_rmse
    except Exception as err:
        print(f"An error occurred: {err}")

# trainer('AAPL')


def predictV2(company_name, date):
    input_dim = 90
    output_dim = 7
    models_folder = "trainedModels"
    print(company_name,date)
    model_path = os.path.join("ml_lib",models_folder, f"{company_name}_trained_model.keras")

    if not os.path.exists(model_path):
        print(f"Model or stats file for {company_name} not found.")
        return None
    model = tf.keras.models.load_model(model_path)
    scaler_file = os.path.join("ml_lib",models_folder, f"{company_name}_scaler.pkl")
    if not os.path.exists(scaler_file):
        print(f"Scaler file for {company_name} not found.")
        return None

    with open(scaler_file, "rb") as f:
        scaler = pickle.load(f)

        historical_data = get_past_history(company=company_name,date=date,size=input_dim)
        last_date = historical_data.index[-1]
        # if date > last_date:
        #     print(f"Date {date} is beyond the available historical data for {company_name}.")
        #     return None
        # if date not in historical_data.index:
        #     print(f"Date {date} not found in historical data for {company_name}.")
        #     return None

        # date_index = historical_data.index.get_loc(date)
        # if date_index < input_dim:
        #     print(f"Not enough data before {date} to make a prediction.")
        #     return None

        previous_data1 = historical_data['Close']
        print(historical_data)
    
        previous_data22 = get_data(company=company_name,date=date,size=input_dim)
        previous_data = np.array([float(i.close_price) for i in previous_data22])
        # for i in previous_data22:
        #     print(f"{i.price_date}       {i.close_price}")
        # previous_data2 = [float(i.close_price) for i in previous_data22]
        # for i in range(input_dim):
        #     print(previous_data1[i],previous_data2[i])

        previous_data = scaler.transform(previous_data.reshape(-1, 1)).reshape(1, input_dim, 1)

        prediction = model.predict(previous_data)
        
        prediction = scaler.inverse_transform(prediction.reshape(-1, 1)).flatten()  # Inverse transform predictions

        # # actual_prices = historical_data['Close'].values[input_dim:input_dim+output_dim]
        # # actual_prices = actual_prices[:len(prediction)]  # Match the length of predictions

        print("Predicted Prices:")
        print(prediction)
        date = pd.Timestamp(date)  # Convert date to pd.Timestamp
        prediction_dates = [date + pd.Timedelta(days=i) for i in range(output_dim)]
        prediction_with_dates = dict(zip(prediction_dates, prediction))
        for i in prediction_with_dates:
            print(i,prediction_with_dates[i])
            #print('\n')
        # #print(prediction_with_dates)
        # # print("\nActual Prices:")
        # # print(actual_prices)
        return prediction.tolist()

# lii = get_all_available_companies()
# for u in lii[:20]:
#     models_folder = "trainedModels"
#     model_path = os.path.join(models_folder, f"{u}_trained_model.keras")
#     if os.path.exists(model_path):
#         print(f"Model for {u} already exists. Skipping training.")
#         continue
#     trainerV2(company_name=u)


# predict('ABT','2025-04-08')

# print(get_past_history('ABT','2025-04-16',10)['Close'])
# predict('AOS','2025-04-08')
# get_data('AOS')['close_pri']
