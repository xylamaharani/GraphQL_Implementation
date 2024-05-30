import graphene
from pprint import pprint
import mysql.connector
from mysql.connector import errorcode
from flask import Flask, request, jsonify
from flask_graphql import GraphQLView
# from graphql.backend import get_default_backend
from functools import wraps



app = Flask(__name__)

## DATABASE CONNECT
config = {
    'user': 'avnadmin',
    'password': 'AVNS_8pk8_VpEMvETZuR__I4',
    'host': 'libratur-database-xylamaharanii-9ca8.b.aivencloud.com',
    'port': '15532',
    'database': 'graphql_eai',
}
conn = mysql.connector.connect(**config)

try:
    conn = mysql.connector.connect(**config)
    print("Connection successful")
    cursor = conn.cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)


## AUTHORIZATION
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != 'admin' or auth.password != 'password':
            return jsonify({'message': 'Authentication required!'}), 401
        return f(*args, **kwargs)
    return decorated


## OBJECT DECLARATION
class TiketPenerbangan(graphene.ObjectType):
    kodePenerbangan = graphene.ID()
    namaMaskapai = graphene.String()
    harga = graphene.Int()

class Keranjang(graphene.ObjectType):
    id = graphene.ID()
    kodePenerbangan = graphene.Int()
    namaPemesan = graphene.String()
    jumlahTiket = graphene.Int()
    harga = graphene.Int()
    totalPrice = graphene.Int()

# Input Types for Mutations
class AddTiketInput(graphene.InputObjectType):
    kodePenerbangan = graphene.Int(required=True)
    namaMaskapai = graphene.String(required=True)
    harga = graphene.Int(required=True)

class AddToKeranjangInput(graphene.InputObjectType):
    kodePenerbangan = graphene.Int(required=True)
    namaPemesan = graphene.String(required=True)
    jumlahTiket = graphene.Int(required=True)

class UpdateKeranjangInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    namaPemesan = graphene.String(required=True)
    kodePenerbangan = graphene.Int(required=True)
    jumlahTiket = graphene.Int(required=True)

class DeleteKeranjangInput(graphene.InputObjectType):
    id = graphene.ID(required=True)



## MUTATION TO INSERT NEW FLIGHT
class AddTiket(graphene.Mutation):
    class Arguments:
        input = AddTiketInput(required=True)

    tiket = graphene.Field(TiketPenerbangan)

    def mutate(self, info, input):
        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()

            # Validate input
            if input.kodePenerbangan < 0:
                raise ValueError("Kode Penerbangan must be a positive integer.")
            if input.harga <= 0:
                raise ValueError("Harga must be a positive integer.")

            add_tiket_query = """
            INSERT INTO tiket_penerbangan (kodePenerbangan, namaMaskapai, harga)
            VALUES (%s, %s, %s)
            """
            cursor.execute(add_tiket_query, (input.kodePenerbangan, input.namaMaskapai, input.harga))
            conn.commit()
            cursor.close()
            conn.close()

            return AddTiket(tiket=TiketPenerbangan(kodePenerbangan=input.kodePenerbangan, namaMaskapai=input.namaMaskapai, harga=input.harga))
        except mysql.connector.Error as err:
            print("Error:", err)
            return None
        except ValueError as ve:
            print("Validation Error:", ve)
            return None




# MUTATION TO INSERT TO KERANJANG
class AddToKeranjang(graphene.Mutation):
    class Arguments:
        input = AddToKeranjangInput(required=True)

    keranjang = graphene.Field(Keranjang)

    def mutate(self, info, input):
        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)

            # Validate input
            if input.kodePenerbangan < 0:
                raise ValueError("Kode Penerbangan must be a positive integer.")
            if input.jumlahTiket <= 0:
                raise ValueError("Jumlah Tiket must be a positive integer.")

            # Get the price of the flight from tiket_penerbangan
            cursor.execute("SELECT harga FROM tiket_penerbangan WHERE kodePenerbangan = %s", (input.kodePenerbangan,))
            flight = cursor.fetchone()

            if not flight:
                raise ValueError("Flight not found")

            totalPrice = flight['harga'] * input.jumlahTiket

            # Insert into keranjang
            add_keranjang_query = """
            INSERT INTO keranjang (namaPemesan, kodePenerbangan, jumlahTiket, totalPrice)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(add_keranjang_query, (input.namaPemesan, input.kodePenerbangan, input.jumlahTiket, totalPrice))
            conn.commit()

            keranjang_id = cursor.lastrowid

            # Query the view to get the total price
            cursor.execute("SELECT * FROM keranjang_view WHERE id = %s", (keranjang_id,))
            keranjang_item = cursor.fetchone()

            cursor.close()
            conn.close()

            if keranjang_item:
                return AddToKeranjang(keranjang=Keranjang(
                    id=keranjang_item['id'],
                    namaPemesan=keranjang_item['namaPemesan'],
                    kodePenerbangan=keranjang_item['kodePenerbangan'],
                    jumlahTiket=keranjang_item['jumlahTiket'],
                    totalPrice=keranjang_item['totalPrice']
                ))
            else:
                raise ValueError("Keranjang item not found")
        except mysql.connector.Error as err:
            print("Database Error:", err)
            return None
        except ValueError as ve:
            print("Validation Error:", ve)
            return None

## MUTATION TO UPDATE KERANJANG
class UpdateKeranjang(graphene.Mutation):
    class Arguments:
        input = UpdateKeranjangInput(required=True)

    keranjang = graphene.Field(Keranjang)

    def mutate(self, info, input):
        try:
            cursor.execute("SELECT * FROM keranjang WHERE id = %s", (input.id,))
            keranjang_item = cursor.fetchone()
            if not keranjang_item:
                raise ValueError("Keranjang item not found")

            # Update the keranjang item
            update_keranjang_query = """
            UPDATE keranjang
            SET namaPemesan = %s, kodePenerbangan = %s, jumlahTiket = %s
            WHERE id = %s
            """
            cursor.execute(update_keranjang_query, (input.namaPemesan, input.kodePenerbangan, input.jumlahTiket, input.id))
            conn.commit()

            # Get the updated item
            cursor.execute("SELECT * FROM keranjang WHERE id = %s", (input.id,))
            updated_item = cursor.fetchone()

            cursor.close()
            conn.close()

            return UpdateKeranjang(keranjang=Keranjang(**updated_item))

        except mysql.connector.Error as err:
            print("Error:", err)
            return None

## MUTATION TO DELETE FROM KERANJANG
class DeleteKeranjang(graphene.Mutation):
    class Arguments:
        input = DeleteKeranjangInput(required=True)

    success = graphene.Boolean()

    def mutate(self, info, input):
        try:
            # Check if the keranjang item exists
            cursor.execute("SELECT * FROM keranjang WHERE id = %s", (input.id,))
            keranjang_item = cursor.fetchone()
            if not keranjang_item:
                raise ValueError("Keranjang item not found")

            # Delete the keranjang item
            delete_keranjang_query = "DELETE FROM keranjang WHERE id = %s"
            cursor.execute(delete_keranjang_query, (input.id,))
            conn.commit()

            cursor.close()
            conn.close()

            return DeleteKeranjang(success=True)

        except mysql.connector.Error as err:
            print("Error:", err)
            return DeleteKeranjang(success=False)


## QUERY AND RESOLVER
class Query(graphene.ObjectType):
    tiket = graphene.Field(TiketPenerbangan, kodePenerbangan=graphene.ID(required=True))
    tikets = graphene.List(TiketPenerbangan)
    keranjang_items = graphene.List(Keranjang)

    def resolve_keranjang_items(self, info):
        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)

            # Query the view
            query_view = "SELECT * FROM keranjang_view"
            cursor.execute(query_view)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            return [Keranjang(**result) for result in results]
        except mysql.connector.Error as err:
            print("Error:", err)
            return []

    def resolve_tiket(self, info, kodePenerbangan):
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tiket_penerbangan WHERE kodePenerbangan = %s", (kodePenerbangan,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return TiketPenerbangan(**result)
        return None

    def resolve_tikets(self, info):
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tiket_penerbangan")
        results = cursor.fetchall()
        cursor.close()
        return [TiketPenerbangan(**result) for result in results]

    def resolve_add_to_keranjang(self, info, input):
        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)

            # Validate input
            if input.kodePenerbangan < 0:
                raise ValueError("Kode Penerbangan must be a positive integer.")
            if input.jumlahTiket <= 0:
                raise ValueError("Jumlah Tiket must be a positive integer.")

            # Get the price of the flight from tiket_penerbangan
            cursor.execute("SELECT harga FROM tiket_penerbangan WHERE kodePenerbangan = %s", (input.kodePenerbangan,))
            flight = cursor.fetchone()

            if not flight:
                raise ValueError("Flight not found")

            totalPrice = flight['harga'] * input.jumlahTiket

            # Insert into keranjang
            add_keranjang_query = """
            INSERT INTO keranjang (namaPemesan, kodePenerbangan, jumlahTiket, totalPrice)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(add_keranjang_query, (input.namaPemesan, input.kodePenerbangan, input.jumlahTiket, totalPrice))
            conn.commit()

            keranjang_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return AddToKeranjang(keranjang=Keranjang(
                id=keranjang_id,
                namaPemesan=input.namaPemesan,
                kodePenerbangan=input.kodePenerbangan,
                jumlahTiket=input.jumlahTiket,
                totalPrice=totalPrice
            ))
        except mysql.connector.Error as err:
            print("Error:", err)
            return None


# Define Mutations
class Mutation(graphene.ObjectType):
    add_tiket = AddTiket.Field()
    add_to_keranjang = AddToKeranjang.Field()
    update_keranjang = UpdateKeranjang.Field()
    delete_keranjang = DeleteKeranjang.Field()


# Create Schema
schema = graphene.Schema(query=Query, mutation=Mutation)

app.add_url_rule('/', view_func=requires_auth(GraphQLView.as_view('graphql', schema=schema, graphiql=True)))

if __name__ == '__main__':
    app.run()