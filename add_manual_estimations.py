# add_manual_estimations.py
import sqlite3
import sys
import os
from config.settings import DATABASE_PATH

def list_cars():
    """
    Affiche la liste des voitures dans la base de données.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, make, model, year, mileage, price, estimated_value
    FROM listings
    ORDER BY id
    """)
    
    cars = cursor.fetchall()
    conn.close()
    
    if not cars:
        print("Aucune voiture dans la base de données.")
        return
    
    print("\n=== VOITURES DANS LA BASE DE DONNÉES ===")
    print(f"{'ID':<4} {'MARQUE':<15} {'MODÈLE':<15} {'ANNÉE':<6} {'KM':<10} {'PRIX':<10} {'ESTIMATION':<10}")
    print("-" * 70)
    
    for car in cars:
        print(f"{car['id']:<4} {car['make'][:14]:<15} {car['model'][:14]:<15} {car['year'] or '?':<6} {car['mileage'] or '?':<10} {car['price'] or '?':<10} {car['estimated_value'] or 'NON':<10}")

def add_estimation(car_id, estimation_value):
    """
    Ajoute une estimation de valeur manuelle pour une voiture.
    
    Args:
        car_id (int): ID de la voiture
        estimation_value (int): Valeur estimée
    
    Returns:
        bool: True si l'opération a réussi, False sinon
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Vérifier si la voiture existe
        cursor.execute("SELECT id FROM listings WHERE id = ?", (car_id,))
        if not cursor.fetchone():
            print(f"Erreur: Aucune voiture avec l'ID {car_id} n'a été trouvée.")
            return False
        
        # Mettre à jour l'estimation
        cursor.execute(
            """
            UPDATE listings
            SET estimated_value = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (estimation_value, car_id)
        )
        
        conn.commit()
        print(f"Estimation ajoutée pour la voiture ID {car_id}: {estimation_value}€")
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de l'ajout de l'estimation: {str(e)}")
        return False
    
    finally:
        conn.close()

def add_percentage_estimations(percentage=90):
    """
    Ajoute des estimations basées sur un pourcentage du prix affiché pour toutes les voitures.
    
    Args:
        percentage (int): Pourcentage du prix affiché à utiliser (par défaut: 90%)
    
    Returns:
        int: Nombre de voitures mises à jour
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        UPDATE listings
        SET estimated_value = CAST(price * ? / 100 AS INTEGER),
            updated_at = CURRENT_TIMESTAMP
        WHERE price IS NOT NULL
          AND estimated_value IS NULL
        """, (percentage,))
        
        count = cursor.rowcount
        conn.commit()
        print(f"{count} estimations ajoutées (à {percentage}% du prix affiché)")
        return count
    
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de l'ajout des estimations: {str(e)}")
        return 0
    
    finally:
        conn.close()

def main():
    """
    Point d'entrée du script.
    """
    # S'assurer que le fichier de base de données existe
    if not os.path.exists(DATABASE_PATH):
        print(f"Erreur: Base de données non trouvée: {DATABASE_PATH}")
        return
    
    # Afficher les options
    print("\n=== AJOUT D'ESTIMATIONS DE PRIX MANUELLES ===")
    print("1. Afficher la liste des voitures")
    print("2. Ajouter une estimation pour une voiture spécifique")
    print("3. Ajouter des estimations automatiques (% du prix affiché)")
    print("4. Quitter")
    
    # Demander à l'utilisateur de choisir une option
    choice = input("\nChoisissez une option (1-4): ")
    
    if choice == "1":
        list_cars()
        main()  # Retour au menu
    
    elif choice == "2":
        car_id = input("ID de la voiture: ")
        try:
            car_id = int(car_id)
        except ValueError:
            print("Erreur: L'ID doit être un nombre entier.")
            main()
            return
        
        estimation = input("Valeur estimée (€): ")
        try:
            estimation = int(estimation)
        except ValueError:
            print("Erreur: La valeur doit être un nombre entier.")
            main()
            return
        
        add_estimation(car_id, estimation)
        main()  # Retour au menu
    
    elif choice == "3":
        percentage = input("Pourcentage du prix affiché à utiliser (par défaut: 90): ")
        try:
            percentage = int(percentage) if percentage else 90
            if percentage <= 0:
                raise ValueError("Le pourcentage doit être positif.")
        except ValueError as e:
            print(f"Erreur: {str(e)}")
            main()
            return
        
        add_percentage_estimations(percentage)
        main()  # Retour au menu
    
    elif choice == "4":
        print("Au revoir!")
        return
    
    else:
        print("Option invalide. Veuillez réessayer.")
        main()

if __name__ == "__main__":
    main()