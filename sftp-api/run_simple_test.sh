#!/bin/bash

# Script simple para ejecutar test y escribir resultado
echo "Ejecutando test simple..."
python3 simple_test.py > simple_test_results.log 2>&1
echo "Test completado. Ver simple_test_results.log"
