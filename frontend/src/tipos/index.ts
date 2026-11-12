export interface Usuario {id:number;nombres:string;apellidos:string;correo:string;nombre_usuario:string;estado:boolean;roles?:string[]}
export interface Modulo {modulo_id:number;codigo:string;nombre:string;activo:boolean}
export interface Sede {id:number;nombre:string;direccion:string;telefono?:string;cantidad_consultorios:number;estado:boolean}

