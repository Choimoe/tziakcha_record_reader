#!/usr/bin/env node
import * as GB from "./calc/js/index.js";

const stdin = await new Promise(r => { let d=""; process.stdin.setEncoding("utf-8"); process.stdin.on("data", c => d+=c); process.stdin.on("end", () => r(d)); });
let input={};
try{ input=JSON.parse(stdin||"{}"); }catch{}
const handStr=input.hand||"";
const result={hand:handStr};
try{
  const { Handtiles, Fan, FAN, FAN_NAME, FAN_SCORE }=GB;
  const ht=new Handtiles();
  const BPhandStr=handStr.replace(/B/g,"P");
  ht.stringToHandtiles(BPhandStr);
  const fan=new Fan();
  const isHu=fan.judgeHu(ht);
  if(!isHu){ result.error="NOT_HU"; }
  else {
    fan.countFan(ht);
    const total=fan.tot_fan_res;
    let base=0; const list=[]; const aliasMap={单钓将:"独听・单钓",边张:"独听・边张",嵌张:"独听・嵌张"};
    for(let i=1;i<FAN.FAN_SIZE;i++){ const score=FAN_SCORE[i]; const name=FAN_NAME[i]; const arr=fan.fan_table_res[i]; if(!arr||arr.length===0) continue; const count=arr.length; const normalizedName=aliasMap[name]||name; if(normalizedName!=="花牌") base+=score*count; list.push({id:i,name,normalizedName,score,count}); }
    const flowerCount=ht.flowerTiles?ht.flowerTiles.length:0;
    result.total_fan=total; result.base_fan=base; result.flowers=flowerCount; result.fan_list=list; result.is_hu=true;
  }
}catch(e){ result.error=String(e.stack||e.message||e); }
process.stdout.write(JSON.stringify(result));
