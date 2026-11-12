import axios from 'axios'
const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://localhost:8000/api'})
api.interceptors.request.use(c=>{const t=localStorage.getItem('access_token');if(t)c.headers.Authorization=`Bearer ${t}`;return c})
let renovando:Promise<string>|null=null
api.interceptors.response.use(r=>r,async error=>{const original=error.config;if(error.response?.status===401&&!original._reintento&&localStorage.getItem('refresh_token')){original._reintento=true;renovando??=api.post('/autenticacion/refrescar-token',{refresh_token:localStorage.getItem('refresh_token')}).then(r=>{localStorage.setItem('access_token',r.data.access_token);localStorage.setItem('refresh_token',r.data.refresh_token);return r.data.access_token}).finally(()=>renovando=null);original.headers.Authorization=`Bearer ${await renovando}`;return api(original)}return Promise.reject(error)})
export default api

