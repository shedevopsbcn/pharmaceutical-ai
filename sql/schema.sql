CREATE DATABASE IF NOT EXISTS ia_farmacia;
USE ia_farmacia;

DROP TABLE IF EXISTS missatges;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS productes;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    cognom VARCHAR(255) NOT NULL,
    farmacia VARCHAR(255) NOT NULL,
    ubicacio VARCHAR(255) NOT NULL,
    correu_electronic VARCHAR(255) NOT NULL UNIQUE,
    contrasenya VARCHAR(255) NOT NULL,
    plan_tipus VARCHAR(50) DEFAULT 'Gratuït'
);

CREATE TABLE productes (
    id INT PRIMARY KEY,
    nom VARCHAR(100),
    quantitat INT,
    miligrams VARCHAR(50),
    preu DECIMAL(10,2),
    data_caducitat DATE,
    proveedor VARCHAR(100),
    categories VARCHAR(100)
);

CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producte_id INT,
    nom VARCHAR(100),
    quantitat_restant INT,
    preu DECIMAL(10,2),
    data_compra DATE
);

CREATE TABLE missatges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255),
    correo VARCHAR(255),
    telefon VARCHAR(50),
    missatge TEXT,
    data_enviament DATETIME DEFAULT CURRENT_TIMESTAMP,
    llegit BOOLEAN DEFAULT FALSE
);