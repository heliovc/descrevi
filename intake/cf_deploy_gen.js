// Deploy do Worker pela API da Cloudflare (sem wrangler login): rode na raiz do repo `node intake/cf_deploy_gen.js`.
// Lê wrangler.toml ([vars], database_id, crons), src/*.js e privado/cloudflare_secrets.env; gera privado/cf/deploy.js
// (contém os segredos; gitignored), que é executado pelo conector Cloudflare (tool execute, code = "$file:<caminho>").
const fs=require("fs"),W="intake/worker/";
const toml=fs.readFileSync(W+"wrangler.toml","utf8");
const varsSec=toml.split(/^\[vars\]\s*$/m)[1];
const vars={};for(const l of varsSec.split("\n")){const m=l.match(/^([A-Z_]+)\s*=\s*"([^"]*)"/);if(m)vars[m[1]]=m[2];}
const compat=toml.match(/compatibility_date\s*=\s*"([^"]+)"/)[1];
const dbid=toml.match(/database_id\s*=\s*"([^"]+)"/)[1];
if(/^0+$/.test(dbid.replace(/-/g,"")))throw new Error("troque o database_id placeholder em wrangler.toml depois de criar o D1 descrevi");
const crons=JSON.parse(toml.match(/crons\s*=\s*(\[[^\]]*\])/)[1]);
const sec={};for(const l of fs.readFileSync("privado/cloudflare_secrets.env","utf8").split("\n")){const m=l.match(/^([A-Z_]+)=(.+)$/);if(m)sec[m[1]]=m[2];}
const mods=["index.js","templates.js"].map(f=>[f,fs.readFileSync(W+"src/"+f,"utf8")]);
const bindings=[{type:"d1",name:"DB",id:dbid},...Object.entries(vars).map(([name,text])=>({type:"plain_text",name,text})),...Object.entries(sec).map(([name,text])=>({type:"secret_text",name,text}))];
const meta={main_module:"index.js",compatibility_date:compat,bindings};
const code=`async () => {
const S="descrevi-intake", A=\`/accounts/\${accountId}/workers/scripts/\${S}\`;
const mods=${JSON.stringify(mods)};
const form=new FormData();
form.append("metadata", new Blob([${JSON.stringify(JSON.stringify(meta))}],{type:"application/json"}));
for (const [n,c] of mods) form.append(n, new Blob([c],{type:"application/javascript+module"}), n);
const up=await cloudflare.request({method:"PUT", path:A, body:form});
const sd=await cloudflare.request({method:"POST", path:A+"/subdomain", body:{enabled:true, previews_enabled:false}});
const sc=await cloudflare.request({method:"PUT", path:A+"/schedules", body:${JSON.stringify(crons.map(c=>({cron:c})))}});
const st=await cloudflare.request({method:"GET", path:A+"/settings"});
return {upload:up.success, etag:up.result?.etag, subdomain:sd.result, schedules:sc.result, bindings:st.result.bindings.map(b=>b.name+":"+b.type), compat:st.result.compatibility_date};
}`;
fs.mkdirSync("privado/cf",{recursive:true,mode:0o700});
fs.writeFileSync("privado/cf/deploy.js",code,{mode:0o600});
console.log("vars:",Object.keys(vars).join(","),"secrets:",Object.keys(sec).join(","),"compat",compat,"crons",crons, "bytes",code.length);
