USE ia_farmacia;

INSERT INTO users (nom, cognom, farmacia, ubicacio, correu_electronic, contrasenya, plan_tipus)
VALUES
('Test', 'User', 'Farmacia Test', 'Barcelona', 'test@test.com', 'password123', 'Premium');

INSERT INTO productes (id, nom, quantitat, miligrams, preu, data_caducitat, proveedor, categories)
VALUES
(1, 'Paracetamol', 46, '500mg', 5.99, '2024-08-30', 'Ubiopharma', 'cap'),
(2, 'Amoxicil·lina', 7, '375mg', 28.99, '2024-09-01', 'Ubiopharma', 'cap'),
(3, 'Omeprazol', 32, '10mg', 12.50, '2024-09-03', 'Farmaplus', 'intestins'),
(4, 'Loratadina', 46, '500mg', 8.75, '2024-09-09', 'Ubiopharma', 'cap'),
(5, 'Metformina', 11, '75mg', 15.20, '2024-09-11', 'Farmaplus', 'peu'),
(6, 'Cetirizina', 28, '50mg', 6.30, '2024-09-13', 'Ubiopharma', 'intestins');

INSERT INTO transactions (producte_id, nom, quantitat_restant, preu, data_compra)
VALUES
(1, 'Paracetamol', 45, 5.99, '2024-08-30'),
(2, 'Amoxicil·lina', 6, 28.99, '2024-09-01'),
(3, 'Omeprazol', 31, 12.50, '2024-09-03'),
(4, 'Loratadina', 45, 8.75, '2024-09-09'),
(5, 'Metformina', 10, 15.20, '2024-09-11'),
(6, 'Cetirizina', 27, 6.30, '2024-09-13');