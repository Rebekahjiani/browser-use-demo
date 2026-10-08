"""Read-only schema and public catalog witnesses. Credentials never enter artifacts."""
import datetime,hashlib,json,pathlib,re,paramiko
from urllib.parse import urlsplit
O=pathlib.Path(__file__).resolve().parent
def export():
 source=pathlib.Path(r'C:\Users\bulin\.crabos_data\file\workspace\default\eval\db-targets.md')
 m=re.search(r'ssh\(([^/]+)/([^ @]+)\s*@([^:]+):(\d+)\)',source.read_text(encoding='utf-8-sig'))
 gold=json.loads((O.parent/'coverage-v3/gold.v1.json').read_text(encoding='utf-8'))
 paths=sorted({urlsplit(f['reference_witness']['url']).path.lstrip('/') for f in gold['facts'] if urlsplit(f['reference_witness']['url']).path.endswith('.html')})
 query_paths=','.join("'"+s.replace("'","''")+"'" for s in paths)
 queries={
 'schema':"SELECT table_name,column_name,data_type,column_key,is_nullable FROM information_schema.columns WHERE table_schema=DATABASE() AND (table_name LIKE 'catalog_product%' OR table_name LIKE 'catalog_category%' OR table_name LIKE 'cataloginventory%' OR table_name LIKE 'eav_%' OR table_name IN ('quote','quote_item','quote_address','review','review_detail','rating_option_vote','url_rewrite')) ORDER BY table_name,ordinal_position",
 'eav':"SELECT t.entity_type_code,a.attribute_id,a.attribute_code,a.frontend_label,a.backend_type,a.backend_table,a.frontend_input,a.is_required FROM eav_attribute a JOIN eav_entity_type t ON a.entity_type_id=t.entity_type_id WHERE t.entity_type_code IN ('catalog_product','catalog_category') ORDER BY t.entity_type_code,a.attribute_id",
 'urls':f"SELECT entity_type,entity_id,request_path,target_path,store_id FROM url_rewrite WHERE request_path IN ({query_paths}) ORDER BY request_path,store_id",
 }
 public_ids=f"SELECT entity_id FROM url_rewrite WHERE entity_type='product' AND request_path IN ({query_paths})"
 queries['products']=f"SELECT entity_id,sku,type_id FROM catalog_product_entity WHERE entity_id IN ({public_ids})"
 for typ in ['varchar','text','int','decimal']:
  queries['product_'+typ]=f"SELECT v.entity_id,v.store_id,a.attribute_code,v.value FROM catalog_product_entity_{typ} v JOIN eav_attribute a ON a.attribute_id=v.attribute_id WHERE v.entity_id IN ({public_ids}) AND a.attribute_code IN ('name','description','short_description','price','image','manufacturer','color','country_of_manufacture','quantity_and_stock_status') ORDER BY v.entity_id,v.store_id,a.attribute_code"
 queries['stock']=f"SELECT product_id,is_in_stock FROM cataloginventory_stock_item WHERE product_id IN ({public_ids})"
 category_ids=f"SELECT entity_id FROM url_rewrite WHERE entity_type='category' AND request_path IN ({query_paths})"
 queries['category_varchar']=f"SELECT v.entity_id,v.store_id,a.attribute_code,v.value FROM catalog_category_entity_varchar v JOIN eav_attribute a ON a.attribute_id=v.attribute_id WHERE v.entity_id IN ({category_ids}) AND a.attribute_code IN ('name','url_key','url_path') ORDER BY v.entity_id,v.store_id,a.attribute_code"
 # Public product evidence only; never read customer, cart or order records.
 php="<?php\n$c=include '/var/www/magento2/app/etc/env.php';$d=$c['db']['connection']['default'];$p=new PDO('mysql:host='.$d['host'].';dbname='.$d['dbname'].';charset=utf8mb4',$d['username'],$d['password']);$p->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$p->exec('SET TRANSACTION READ ONLY');$p->beginTransaction();$qs=json_decode(base64_decode('"
 import base64
 php+=base64.b64encode(json.dumps(queries).encode()).decode()+"'),true);$out=[];foreach($qs as $k=>$q){$out[$k]=$p->query($q)->fetchAll(PDO::FETCH_ASSOC);}$p->rollBack();echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE);"
 c=paramiko.SSHClient();c.load_system_host_keys()
 try:
  c.connect(m[3],port=int(m[4]),username=m[1],password=m[2],timeout=15,look_for_keys=False,allow_agent=False)
  inp,out,err=c.exec_command('sudo -n docker exec -i webarena_verified_shopping php',timeout=50)
  inp.write(php);inp.flush();inp.channel.shutdown_write();raw=out.read();code=out.channel.recv_exit_status()
  if code:raise RuntimeError('Read-only database export failed; exit '+str(code))
  data=json.loads(raw)
 finally:c.close()
 dest=O/'db-export.v2.json'
 if dest.exists():raise RuntimeError('Refuse overwrite')
 artifact={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'webarena_verified_shopping / configured Magento database','method':'PDO read-only transaction rolled back; information_schema, EAV metadata, public catalog only','queries':queries,'data':data}
 dest.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rows':{k:len(v) for k,v in data.items()}},indent=2))
if __name__=='__main__':export()
