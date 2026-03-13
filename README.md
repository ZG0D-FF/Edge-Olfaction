# Hybrid Edge-Olfaction Logistics 🍓💨
**Predictive Spoilage Detection via Biochemical Gas Monitoring**

## Overview
This repository contains the logic and edge-computing framework for an "Electronic Nose" designed to monitor perishable goods. By utilizing a fusion of MQ-series gas sensors, the system detects organic off-gassing (like ethylene and alcohol) from decaying produce. 

The core engine uses **Arrhenius-based decay modeling** to calculate spoilage risk in real-time, functioning as an early-warning system for agricultural and supply-chain logistics.

## Hardware Architecture
* **Central Hub:** Raspberry Pi 3B+ 
* **Sensor Nodes:** Arduino Uno (ADC processing)
* **Sensor Array:** MQ-135 (Air Quality), MQ-3 (Alcohol), MQ-4 (Methane), DHT11 (Temp/Humidity)

## Software Stack
* **Logic Layer:** Python (Raspberry Pi execution & math modeling)
* **Data Parsing:** Serial Communication (PySerial)
* **Alert System:** IoT Telegram Bot Integration (`@dj_jarvis_sentry_bot`)

## Execution
The system reads analog voltage values from the MQ sensors, converts them to PPM (Parts Per Million) based on load resistance calibration, and applies the Arrhenius equation alongside temperature data to predict shelf-life degradation.
