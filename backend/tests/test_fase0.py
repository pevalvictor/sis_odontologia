def registro(cliente,ruc="20123456789",correo="admin@uno.example.com"):
    return cliente.post("/api/autenticacion/registro-inicial",json={"nombre_comercial":"Clínica Uno","ruc":ruc,"correo_clinica":f"contacto{ruc}@example.com","nombres_administrador":"Ana","apellidos_administrador":"Pérez","correo_administrador":correo,"nombre_usuario":"admin","contrasena":"Segura123*"})
def token(cliente,ruc="20123456789"):
    r=cliente.post("/api/autenticacion/iniciar-sesion",json={"identificador":"admin","contrasena":"Segura123*","ruc":ruc});return r.json()["access_token"]
def test_registro_login_y_hash_oculto(cliente):
    assert registro(cliente).status_code==201
    h={"Authorization":f"Bearer {token(cliente)}"};r=cliente.get("/api/autenticacion/mi-perfil",headers=h)
    assert r.status_code==200 and "contrasena_hash" not in r.json()
def test_aislamiento_entre_clinicas(cliente):
    registro(cliente);registro(cliente,"20999999999","admin@dos.example.com")
    h1={"Authorization":f"Bearer {token(cliente)}"};h2={"Authorization":f"Bearer {token(cliente,'20999999999')}"}
    cliente.post("/api/sedes",headers=h1,json={"nombre":"Sede privada","direccion":"Lima"})
    assert cliente.get("/api/sedes",headers=h2).json()==[]
def test_modulo_y_permiso_protegen_ruta(cliente):
    registro(cliente);h={"Authorization":f"Bearer {token(cliente)}"}
    assert cliente.get("/api/usuarios",headers=h).status_code==200
    assert cliente.get("/api/sedes",headers=h).status_code==200
