'use strict';
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {minify}=require('html-minifier-terser');
const CleanCSS=require('clean-css');
const Obfuscator=require('javascript-obfuscator');
const pages=['web/index.html','web/beta.html'];
const hash=t=>crypto.createHash('sha256').update(t).digest('hex').slice(0,16);
const options={
  compact:true,
  controlFlowFlattening:false,
  deadCodeInjection:false,
  debugProtection:false,
  disableConsoleOutput:false,
  identifierNamesGenerator:'hexadecimal',
  numbersToExpressions:false,
  renameGlobals:false,
  selfDefending:false,
  simplify:true,
  splitStrings:false,
  stringArray:true,
  stringArrayCallsTransform:false,
  stringArrayEncoding:['base64'],
  stringArrayRotate:true,
  stringArrayShuffle:true,
  stringArrayThreshold:0.8,
  transformObjectKeys:false,
  unicodeEscapeSequence:false
};
async function main(){
  fs.mkdirSync('web/assets',{recursive:true});
  for(const page of pages){
    const source=fs.readFileSync(page,'utf8');
    const already=/data-mxd-protected=["']1["']/.test(source);
    if(already){
      if(/<script(?:\s[^>]*)?>\s*\S[\s\S]*?<\/script>/i.test(source) ||
         /<style\b[^>]*>[\s\S]*?\S[\s\S]*?<\/style>/i.test(source))
        throw Error('Protected document contains new inline source: '+page);
      console.log('Already protected:',page);
      continue;
    }
    const scripts=[...source.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
    const styles=[...source.matchAll(/<style\b([^>]*)>([\s\S]*?)<\/style\s*>/gi)];
    assert.equal(scripts.length,1,'Unexpected script count in '+page);
    assert.equal(styles.length,1,'Unexpected style count in '+page);
    assert.ok(scripts[0][2].trim().length>1000,'Unexpected script contents in '+page);
    assert.ok(styles[0][2].trim().length>1000,'Unexpected CSS contents in '+page);
    assert.ok(!/\bsrc\s*=/.test(scripts[0][1]),'Expected inline script in '+page);
    const protectedJS=Obfuscator.obfuscate(scripts[0][2],options).getObfuscatedCode();
    assert.ok(protectedJS.length>1000,'Unexpectedly small obfuscation output');
    const cssResult=new CleanCSS({level:1}).minify(styles[0][2]);
    if(cssResult.errors.length)throw Error('CSS minification failed: '+cssResult.errors.join(' | '));
    const jsName='mxd-'+hash(page+'\njs\n'+scripts[0][2])+'.js';
    const cssName='mxd-'+hash(page+'\ncss\n'+styles[0][2])+'.css';
    fs.writeFileSync('web/assets/'+jsName,protectedJS+'\n');
    fs.writeFileSync('web/assets/'+cssName,cssResult.styles+'\n');
    let html=source.replace(scripts[0][0],'<script data-mxd-protected="1" src="/assets/'+jsName+'"></script>');
    html=html.replace(styles[0][0],'<link rel="stylesheet" href="/assets/'+cssName+'">');
    html=await minify(html,{
      collapseWhitespace:true,
      conservativeCollapse:true,
      removeComments:true,
      removeEmptyAttributes:false,
      removeOptionalTags:false,
      removeAttributeQuotes:false,
      removeRedundantAttributes:false,
      minifyCSS:false,
      minifyJS:false,
      sortAttributes:false,
      sortClassName:false,
      caseSensitive:true
    });
    assert.ok(html.includes(jsName)&&html.includes(cssName),'External assets missing from HTML');
    assert.ok(!html.includes(scripts[0][2].slice(40,100)),'Original script leaked into HTML');
    assert.ok(html.includes('data-mxd-protected="1"'),'Protection marker missing');
    fs.writeFileSync(page,html+'\n');
    console.log(page,'protected',scripts[0][2].length,'JS source chars and',
      styles[0][2].length,'CSS chars:',jsName,cssName);
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});