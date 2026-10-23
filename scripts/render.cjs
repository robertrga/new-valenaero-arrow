const fs=require('fs'),path=require('path');
const sharp=require('sharp');
const portable=path.basename(__dirname)==='scripts';
const base=portable?path.join(__dirname,'..','sources','svg'):path.join(__dirname,'apple_cursor','svg');
const out=portable?path.join(__dirname,'..','.cache','rasters'):path.join(__dirname,'apple_rasters');fs.mkdirSync(out,{recursive:true});
async function render(file,name,work=false){
 let svg=fs.readFileSync(file,'utf8');
 if(name.endsWith('_badge')){
  const original=svg;
  svg=svg.replace(/<g filter="url\(#filter\d+_d_[^)]+\)">\s*<path[^>]*fill="#00FF00"[^>]*\/>\s*<\/g>/g,'');
  if(svg===original)throw Error('Arrow removal failed: '+name);
 }
 svg=svg.replace(/#00FF00/gi,'#000000').replace(/#0000FF/gi,'#FFFFFF');
 if(work){
  // Keep the first filtered group (the animated Apple disc), remove the arrow groups.
  const start=svg.indexOf('<g filter="url(#filter1_');
  const end=svg.indexOf('<defs>');
  if(start<0||end<start)throw Error('Unexpected animated SVG structure');
  svg=svg.slice(0,start)+'</g>\n'+svg.slice(end);
 }
 await sharp(Buffer.from(svg),{density:384}).resize(1028,1028).png().toFile(path.join(out,name+'.png'));
}
(async()=>{
 const names=['all-scroll','bottom_left_corner','bottom_right_corner','cross','crossed_circle','hand2','pencil','question_arrow','right_ptr','sb_h_double_arrow','sb_v_double_arrow','xterm','person','pin'];
 for(const n of names)await render(path.join(base,n+'.svg'),n);
 for(const n of ['pin','person','crossed_circle'])await render(path.join(base,n+'.svg'),n+'_badge');
 for(const group of ['wait','left_ptr_watch'])
  for(const f of fs.readdirSync(path.join(base,group)).filter(f=>f.endsWith('.svg')).sort())
   await render(path.join(base,group,f),f.slice(0,-4),group==='left_ptr_watch');
 console.log('Rendered all Apple assets, including 80 animation frames.');
})().catch(e=>{console.error(e);process.exit(1)});
