# -*- coding: utf-8 -*-
"""
pronostico_modelos.py
------------------------
Sesion 8 - Pronostico.

Decision documentada (BRAI): el temario original sugiere ARIMA, Prophet y
LSTM como si fueran opciones intercambiables. Con solo 28 observaciones
diarias eso no es razonable asumirlo sin probar -- se prueban los 3, mas
un baseline obligatorio, y se comparan con evidencia (MAE/RMSE en un
holdout), replicando el mismo criterio de "probar antes de descartar" que
ya se aplico con GDELT en la Sesion 4.

Sustitucion de LSTM por restriccion de entorno (documentar tal cual):
  El sandbox de trabajo se quedo sin espacio en disco al instalar
  TensorFlow/PyTorch (~3.2 GB libres, insuficiente). En su lugar se usa
  MLPRegressor de scikit-learn (ya instalado) sobre una ventana de
  rezagos (lag features) como sustituto de una red neuronal secuencial.
  No es una LSTM real (no tiene memoria recurrente), pero comparte la
  propiedad relevante para esta prueba: es un modelo con muchos mas
  parametros que datos de entrenamiento, por lo que sirve para ilustrar
  el mismo modo de falla esperado (sobreajuste con 21 puntos de
  entrenamiento). Se documenta la sustitucion, no se oculta.

Particion:
  Entrenamiento: 2026-07-10 a 2026-07-30 (21 dias)
  Prueba (holdout): 2026-07-31 a 2026-08-06 (7 dias)

Nota sobre el 27 de julio: se sabe (verificacion de la Sesion 7) que ese
0 es una anomalia de captura, no un cero editorial real. Cae dentro del
set de entrenamiento -- se deja tal cual (sin imputar) para que el
efecto de esa distorsion sea visible en los resultados, y se comenta
en las conclusiones.

Salida:
  - pronosticos_comparacion.csv (metricas MAE/RMSE por modelo)
  - pronosticos_comparacion.png (serie real vs. cada pronostico)

Uso:
    python pronostico_modelos.py
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet

RUTA_SERIE = "series_diarias.csv"
COL_OBJETIVO = "total_articulos"
DIAS_TEST = 7


def cargar_serie():
    df = pd.read_csv(RUTA_SERIE, parse_dates=["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    return df


def dividir_train_test(df):
    train = df.iloc[:-DIAS_TEST].copy()
    test = df.iloc[-DIAS_TEST:].copy()
    return train, test


def evaluar(y_true, y_pred, nombre):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{nombre:25} MAE={mae:6.2f}   RMSE={rmse:6.2f}")
    return {"modelo": nombre, "MAE": round(mae, 2), "RMSE": round(rmse, 2)}


def modelo_naive(train, n_pred):
    ultimo_valor = train[COL_OBJETIVO].iloc[-1]
    return np.full(n_pred, ultimo_valor)


def modelo_media_movil(train, n_pred, ventana=5):
    media = train[COL_OBJETIVO].iloc[-ventana:].mean()
    return np.full(n_pred, media)


def modelo_arima(train, n_pred):
    # Busqueda pequena de ordenes -- la serie es corta, no tiene caso una
    # busqueda exhaustiva tipo auto_arima; se prueban ordenes razonables
    # dado que hay una tendencia clara de caida (se espera necesitar
    # diferenciacion, d=1).
    ordenes_candidatas = [(1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 1), (1, 1, 2)]
    mejor_aic = np.inf
    mejor_modelo = None
    mejor_orden = None
    serie = train[COL_OBJETIVO].values
    for orden in ordenes_candidatas:
        try:
            m = ARIMA(serie, order=orden).fit()
            if m.aic < mejor_aic:
                mejor_aic = m.aic
                mejor_modelo = m
                mejor_orden = orden
        except Exception:
            continue
    print(f"  -> ARIMA: mejor orden por AIC = {mejor_orden} (AIC={mejor_aic:.1f})")
    pred = mejor_modelo.forecast(steps=n_pred)
    return np.clip(pred, 0, None)  # no tiene sentido pronosticar articulos negativos


def modelo_prophet(train, fechas_test):
    df_prophet = train[["fecha", COL_OBJETIVO]].rename(
        columns={"fecha": "ds", COL_OBJETIVO: "y"})
    m = Prophet(
        daily_seasonality=False,
        weekly_seasonality=False,  # 21 dias = 3 semanas, insuficiente para estimarla en serio
        yearly_seasonality=False,
        changepoint_prior_scale=0.5,  # mas flexible: la serie tiene un quiebre fuerte post-pico
    )
    m.fit(df_prophet)
    futuro = pd.DataFrame({"ds": fechas_test})
    pred = m.predict(futuro)
    return np.clip(pred["yhat"].values, 0, None)


def construir_features_rezago(serie, n_lags=3):
    X, y = [], []
    for i in range(n_lags, len(serie)):
        X.append(serie[i - n_lags:i])
        y.append(serie[i])
    return np.array(X), np.array(y)


def modelo_red_neuronal_sustituto(train, test, n_pred, n_lags=3):
    """Sustituto de LSTM (ver nota BRAI en el docstring del modulo)."""
    serie_train = train[COL_OBJETIVO].values
    X_train, y_train = construir_features_rezago(serie_train, n_lags)

    if len(X_train) < 5:
        print("  -> Insuficientes muestras de entrenamiento para el sustituto "
              "de red neuronal, se omite (evidencia adicional de falta de datos).")
        return None

    mlp = MLPRegressor(hidden_layer_sizes=(8,), max_iter=3000, random_state=42)
    mlp.fit(X_train, y_train)

    # Pronostico recursivo: usa sus propias predicciones como input del
    # siguiente paso (igual que haria una LSTM en modo autoregresivo)
    historial = list(serie_train[-n_lags:])
    predicciones = []
    for _ in range(n_pred):
        entrada = np.array(historial[-n_lags:]).reshape(1, -1)
        pred = mlp.predict(entrada)[0]
        predicciones.append(pred)
        historial.append(pred)

    return np.clip(np.array(predicciones), 0, None)


def main():
    df = cargar_serie()
    train, test = dividir_train_test(df)

    print(f"Entrenamiento: {train['fecha'].min().date()} a {train['fecha'].max().date()} "
          f"({len(train)} dias)")
    print(f"Prueba (holdout): {test['fecha'].min().date()} a {test['fecha'].max().date()} "
          f"({len(test)} dias)")
    print(f"\nNota: el 27-jul (0 articulos, anomalia de captura conocida) esta "
          f"dentro del set de entrenamiento.\n")

    y_test = test[COL_OBJETIVO].values
    resultados = []
    pronosticos = {"fecha": test["fecha"].values, "real": y_test}

    print("="*60)
    print("EVALUACION DE MODELOS (holdout de 7 dias)")
    print("="*60)

    pred = modelo_naive(train, len(test))
    resultados.append(evaluar(y_test, pred, "Naive (ultimo valor)"))
    pronosticos["naive"] = pred

    pred = modelo_media_movil(train, len(test), ventana=5)
    resultados.append(evaluar(y_test, pred, "Media movil (ventana=5)"))
    pronosticos["media_movil"] = pred

    pred = modelo_arima(train, len(test))
    resultados.append(evaluar(y_test, pred, "ARIMA"))
    pronosticos["arima"] = pred

    pred = modelo_prophet(train, test["fecha"].values)
    resultados.append(evaluar(y_test, pred, "Prophet"))
    pronosticos["prophet"] = pred

    pred = modelo_red_neuronal_sustituto(train, test, len(test))
    if pred is not None:
        resultados.append(evaluar(y_test, pred, "Red neuronal (sustituto LSTM)"))
        pronosticos["red_neuronal"] = pred

    df_resultados = pd.DataFrame(resultados).sort_values("MAE")
    print("\n" + "="*60)
    print("RANKING FINAL (por MAE, menor es mejor)")
    print("="*60)
    print(df_resultados.to_string(index=False))

    df_resultados.to_csv("pronosticos_comparacion.csv", index=False)
    pd.DataFrame(pronosticos).to_csv("pronosticos_detalle.csv", index=False)

    # Grafico comparativo
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df["fecha"], df[COL_OBJETIVO], color="black", marker="o",
            markersize=3, linewidth=1.3, label="Real (serie completa)")
    colores = {"naive": "#999999", "media_movil": "#e6b800", "arima": "#2b6cb0",
               "prophet": "#2f855a", "red_neuronal": "#c05621"}
    for col, color in colores.items():
        if col in pronosticos:
            ax.plot(pronosticos["fecha"], pronosticos[col], linestyle="--",
                    marker="s", markersize=4, color=color, label=col)
    ax.axvspan(test["fecha"].min(), test["fecha"].max(), alpha=0.08, color="red")
    ax.set_title("Pronosticos vs. valor real (zona roja = holdout de evaluacion)")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Articulos publicados")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig("pronosticos_comparacion.png", dpi=150)
    print("\nGrafico guardado en: pronosticos_comparacion.png")


if __name__ == "__main__":
    main()