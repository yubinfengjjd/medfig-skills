#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [object]$Illustrator,

    [Parameter(Mandatory = $true)]
    [string]$RootGroupName,

    [Parameter(Mandatory = $true)]
    [string]$CachePath,

    [Parameter(Mandatory = $true)]
    [string]$ApprovedSvg,

    [Parameter(Mandatory = $true)]
    [string]$OutputReport,

    [switch]$RepairText
)

$ErrorActionPreference = 'Stop'
$diagnosticHelpers = Join-Path $PSScriptRoot 'layout_diagnostics.ps1'
. $diagnosticHelpers
$cacheFile = (Resolve-Path -LiteralPath $CachePath).Path
$svgFile = (Resolve-Path -LiteralPath $ApprovedSvg).Path
$reportFile = [IO.Path]::GetFullPath($OutputReport)
$cache = Get-Content -LiteralPath $cacheFile -Raw -Encoding UTF8 | ConvertFrom-Json
[xml]$svg = Get-Content -LiteralPath $svgFile -Raw -Encoding UTF8

$atomsBySourceId = @{}
foreach ($atom in $cache.atoms) {
    if (-not [string]::IsNullOrWhiteSpace([string]$atom.sourceId)) {
        $atomsBySourceId[[string]$atom.sourceId] = $atom
    }
}

$entries = @()
$textNodes = $svg.SelectNodes("//*[local-name()='text']")
foreach ($node in $textNodes) {
    $id = [string]$node.GetAttribute('id')
    $containerId = [string]$node.GetAttribute('data-container-id')
    if ([string]::IsNullOrWhiteSpace($id) -or -not $atomsBySourceId.ContainsKey($id)) { continue }
    $fontSize = 16.0
    if (-not [double]::TryParse([string]$node.GetAttribute('font-size'), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$fontSize)) {
        $fontSize = 16.0
    }
    $allowed = @()
    $allowedRaw = [string]$node.GetAttribute('data-overlap-allow')
    if (-not [string]::IsNullOrWhiteSpace($allowedRaw)) {
        $allowed = @($allowedRaw -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    $entries += [ordered]@{
        id = $id
        objectName = [string]$atomsBySourceId[$id].objectName
        containerId = $containerId
        layoutGroup = [string]$node.GetAttribute('data-layout-group')
        containerObjectName = if ([string]::IsNullOrWhiteSpace($containerId)) {
            ''
        } elseif ($atomsBySourceId.ContainsKey($containerId)) {
            [string]$atomsBySourceId[$containerId].objectName
        } else {
            '__MISSING_CONTAINER__' + $containerId
        }
        originalText = [string]$node.InnerText
        originalFontSize = $fontSize
        fontFamily = [string]$atomsBySourceId[$id].text.fontFamily
        fontWeight = [string]$atomsBySourceId[$id].text.fontWeight
        fontStyle = [string]$atomsBySourceId[$id].text.fontStyle
        fontFloor = [Math]::Max(8.0, $fontSize * 0.75)
        paddingMultiple = 0.5
        allowedOverlapIds = $allowed
    }
}

$obstacles = @()
foreach ($node in $svg.SelectNodes("//*")) {
    $id = [string]$node.GetAttribute('id')
    $role = [string]$node.GetAttribute('data-collision-role')
    # Opt-in raster panels are obstacles by default, matching the SVG preflight.
    if ([string]::IsNullOrWhiteSpace($role) -and $node.LocalName -eq 'image') { $role = 'obstacle' }
    if ([string]::IsNullOrWhiteSpace($id) -or -not $atomsBySourceId.ContainsKey($id)) { continue }
    if ($role -notin @('obstacle', 'connector', 'arrow', 'icon', 'node', 'frame')) { continue }
    $atom = $atomsBySourceId[$id]
    $paintNames = @()
    if (@($atom.paintParts).Count -le 1) {
        $paintNames = @([string]$atom.objectName)
    } else {
        for ($paintIndex = 0; $paintIndex -lt @($atom.paintParts).Count; $paintIndex++) {
            $paintNames += "$([string]$atom.objectName)_P$paintIndex"
        }
    }
    $allowed = @()
    $allowedRaw = [string]$node.GetAttribute('data-overlap-allow')
    if (-not [string]::IsNullOrWhiteSpace($allowedRaw)) {
        $allowed = @($allowedRaw -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    $obstacles += [ordered]@{
        id = $id
        objectNames = $paintNames
        role = $role
        layoutGroup = [string]$node.GetAttribute('data-layout-group')
        allowedOverlapIds = $allowed
    }
}

$configuration = [ordered]@{
    rootGroupName = $RootGroupName
    repairText = $RepairText.IsPresent
    entries = $entries
    obstacles = $obstacles
}
$payload = ConvertTo-Json $configuration -Compress -Depth 12
$script = @"
(function(){
  var c=$payload;
  function findRoot(){
    var d=app.activeDocument;
    for(var i=0;i<d.groupItems.length;i+=1){try{if(d.groupItems[i].name===c.rootGroupName)return d.groupItems[i];}catch(ignore){}}
    return null;
  }
  function findNamed(container,name){
    try{for(var p=0;p<container.pageItems.length;p+=1){var item=container.pageItems[p];if(item&&item.name===name)return item;}}catch(ignorePage){}
    try{for(var g=0;g<container.groupItems.length;g+=1){var found=findNamed(container.groupItems[g],name);if(found!==null)return found;}}catch(ignoreGroups){}
    return null;
  }
  function bounds(item){var b=item.visibleBounds;return {l:b[0],t:b[1],r:b[2],b:b[3]};}
  function fits(textItem,boxItem,pad){
    var t=bounds(textItem),b=bounds(boxItem);
    return t.l>=b.l+pad-0.5&&t.r<=b.r-pad+0.5&&t.t<=b.t-pad+0.5&&t.b>=b.b+pad-0.5;
  }
  function intersects(a,b){return Math.min(a.r,b.r)-Math.max(a.l,b.l)>0.5&&Math.min(a.t,b.t)-Math.max(a.b,b.b)>0.5;}
  function segmentHits(x1,y1,x2,y2,b){
    var dx=x2-x1,dy=y2-y1,lo=0,hi=1,p=[-dx,dx,-dy,dy],q=[x1-b.l,b.r-x1,y1-b.b,b.t-y1];
    for(var i=0;i<4;i++){if(Math.abs(p[i])<1e-9){if(q[i]<0)return false;continue;}var r=q[i]/p[i];if(p[i]<0)lo=Math.max(lo,r);else hi=Math.min(hi,r);if(lo>hi)return false;}return true;
  }
  function graphicHits(textBounds,item,role){
    if(role==='connector'&&item.typename==='PathItem'){
      try{for(var i=1;i<item.pathPoints.length;i++){var a=item.pathPoints[i-1].anchor,z=item.pathPoints[i].anchor;if(segmentHits(a[0],a[1],z[0],z[1],textBounds))return true;}}catch(ignorePath){}
      return false;
    }
    return intersects(textBounds,bounds(item));
  }
  function centerText(textItem,boxItem){
    var t=bounds(textItem),b=bounds(boxItem);
    var tx=(b.l+b.r-t.l-t.r)/2;
    var ty=(b.t+b.b-t.t-t.b)/2;
    textItem.translate(tx,ty);
  }
  function splitText(value){
    var words=value.replace(/[\r\n]+/g,' ').split(/\s+/),best=-1,difference=1e9,total=value.length;
    if(words.length<2)return null;
    var used=0;
    for(var i=0;i<words.length-1;i+=1){used+=words[i].length+(i?1:0);var d=Math.abs(total/2-used);if(d<difference){difference=d;best=i;}}
    if(best<0)return null;
    return words.slice(0,best+1).join(' ')+'\r'+words.slice(best+1).join(' ');
  }
  function centerGroup(items,boxItem){
    var b=bounds(boxItem),l=1e20,r=-1e20,t=-1e20,bot=1e20;
    for(var i=0;i<items.length;i+=1){var v=bounds(items[i].text);l=Math.min(l,v.l);r=Math.max(r,v.r);t=Math.max(t,v.t);bot=Math.min(bot,v.b);}
    var tx=(b.l+b.r-l-r)/2,ty=(b.t+b.b-t-bot)/2;
    if(Math.abs(tx)>0.01||Math.abs(ty)>0.01){for(var z=0;z<items.length;z+=1)items[z].text.translate(tx,ty);return 1;}
    return 0;
  }
  function resolveTextFont(entry){
    var preferred=entry.fontFamily||'Arial',preferredLower=preferred.toLowerCase();
    var weight=String(entry.fontWeight||'').toLowerCase(),fontStyle=String(entry.fontStyle||'').toLowerCase();
    var wantsBold=weight.indexOf('bold')>=0||parseInt(weight,10)>=600;
    var wantsItalic=fontStyle.indexOf('italic')>=0||fontStyle.indexOf('oblique')>=0;
    var best=null,bestScore=-100000;
    for(var i=0;i<app.textFonts.length;i+=1){try{
      var candidate=app.textFonts[i],candidateFamily=(candidate.family||candidate.name||'').toLowerCase(),candidateName=(candidate.name||'').toLowerCase();
      if(candidateFamily!==preferredLower&&candidateName!==preferredLower)continue;
      var styleLower=(candidate.style||'').toLowerCase();
      var candidateBold=styleLower.indexOf('bold')>=0||styleLower.indexOf('semibold')>=0||styleLower.indexOf('demi')>=0;
      var candidateHeavy=styleLower.indexOf('black')>=0||styleLower.indexOf('heavy')>=0;
      var candidateItalic=styleLower.indexOf('italic')>=0||styleLower.indexOf('oblique')>=0;
      var candidateCondensed=styleLower.indexOf('narrow')>=0||styleLower.indexOf('condensed')>=0;
      var score=0;
      if(candidateFamily===preferredLower)score+=100;if(candidateName===preferredLower)score+=10;
      score+=candidateBold===wantsBold?40:-40;score+=candidateItalic===wantsItalic?40:-40;
      if(!wantsBold&&!wantsItalic&&(styleLower==='regular'||styleLower==='roman'||styleLower==='normal'))score+=30;
      if(wantsBold&&styleLower==='bold')score+=30;
      if(wantsItalic&&!wantsBold&&styleLower==='italic')score+=30;
      if(wantsBold&&wantsItalic&&styleLower==='bold italic')score+=30;
      if(candidateHeavy)score-=80;if(candidateCondensed)score-=40;
      if(score>bestScore){best=candidate;bestScore=score;}
    }catch(ignoreFont){}}
    if(best!==null)return best;
    try{return app.textFonts.getByName('ArialMT');}catch(ignoreFallbackFont){}
    return null;
  }
  function canonicalContent(value){return String(value||'').replace(/\r\n/g,'\r').replace(/\n/g,'\r');}
  var root=findRoot();if(root===null)return 'ERROR|ROOT_NOT_FOUND';
  var repairCount=0,issues=[],resolved=[],groups={};
  for(var i=0;i<c.entries.length;i+=1){
    var e=c.entries[i],textItem=findNamed(root,e.objectName),boxItem=e.containerObjectName?findNamed(root,e.containerObjectName):null;
    if(textItem===null||(e.containerObjectName&&boxItem===null)){issues.push('MISSING:'+e.id);continue;}
    var approvedContent=canonicalContent(e.originalText),currentContent=canonicalContent(textItem.contents);
    if(currentContent!==approvedContent&&c.repairText){textItem.contents=approvedContent;repairCount+=1;currentContent=canonicalContent(textItem.contents);}
    if(currentContent!==approvedContent)issues.push('TEXT_CONTENT_MISMATCH:'+e.id);
    var expectedFont=resolveTextFont(e);
    if(expectedFont===null){issues.push('FONT_UNAVAILABLE:'+e.id);}
    else{
      var currentFontName='';try{currentFontName=String(textItem.textRange.characterAttributes.textFont.name);}catch(ignoreCurrentFont){}
      if(currentFontName!==String(expectedFont.name)&&c.repairText){textItem.textRange.characterAttributes.textFont=expectedFont;repairCount+=1;currentFontName=String(textItem.textRange.characterAttributes.textFont.name);}
      if(currentFontName!==String(expectedFont.name))issues.push('FONT_MISMATCH:'+e.id);
    }
    var resolvedItem={entry:e,text:textItem,box:boxItem};resolved.push(resolvedItem);
    if(boxItem!==null){if(!groups[e.containerObjectName])groups[e.containerObjectName]=[];groups[e.containerObjectName].push(resolvedItem);}
  }
  for(var groupName in groups){if(!groups.hasOwnProperty(groupName))continue;
    var group=groups[groupName],box=group[0].box;
    if(group.length===1){
      var one=group[0],current=Number(one.text.textRange.characterAttributes.size),floor=Math.max(8.0,current*0.75);
      if(!fits(one.text,box,current*Number(one.entry.paddingMultiple))&&c.repairText){
        centerText(one.text,box);repairCount+=1;current=Number(one.text.textRange.characterAttributes.size);
        var centeredTextBounds=bounds(one.text),centeredBoxBounds=bounds(box),singlePad=current*Number(one.entry.paddingMultiple);
        if(centeredTextBounds.r-centeredTextBounds.l>centeredBoxBounds.r-centeredBoxBounds.l-2*singlePad){
          var wrapped=splitText(String(one.text.contents));if(wrapped!==null){one.text.contents=wrapped;repairCount+=1;centerText(one.text,box);}
        }
        while(current-0.5>=floor&&!fits(one.text,box,current*Number(one.entry.paddingMultiple))){current-=0.5;one.text.textRange.characterAttributes.size=current;centerText(one.text,box);repairCount+=1;}
      }
    }else if(c.repairText){
      // Multiple SVG text atoms in one box are intentional title/subtitle
      // stacks. Move them as one block; centering each atom would collapse all
      // lines onto the same baseline.
      repairCount+=centerGroup(group,box);
      for(var gp=0;gp<group.length;gp+=1)group[gp].floor=Math.max(8.0,Number(group[gp].text.textRange.characterAttributes.size)*0.75);
      var changed=true;
      while(changed){
        changed=false;
        for(var gi=0;gi<group.length;gi+=1){
          var member=group[gi],size=Number(member.text.textRange.characterAttributes.size),memberFloor=member.floor;
          if(!fits(member.text,box,size*Number(member.entry.paddingMultiple))&&size-0.5>=memberFloor){member.text.textRange.characterAttributes.size=size-0.5;repairCount+=1;changed=true;}
        }
        if(changed)repairCount+=centerGroup(group,box);
      }
    }
    for(var gf=0;gf<group.length;gf+=1){var finalSize=Number(group[gf].text.textRange.characterAttributes.size);if(!fits(group[gf].text,box,finalSize*Number(group[gf].entry.paddingMultiple)))issues.push('TEXT_CONTAINER_OVERFLOW:'+group[gf].entry.id);}
  }
  for(var rf=0;rf<resolved.length;rf+=1){if(Number(resolved[rf].text.textRange.characterAttributes.size)<8.0-0.01)issues.push('FONT_BELOW_MINIMUM:'+resolved[rf].entry.id);}
  var obstacleItems=[];
  for(var oi=0;oi<c.obstacles.length;oi+=1){var oe=c.obstacles[oi];for(var on=0;on<oe.objectNames.length;on+=1){var nativeObstacle=findNamed(root,oe.objectNames[on]);if(nativeObstacle!==null)obstacleItems.push({entry:oe,item:nativeObstacle});}}
  function overlapAllowed(textEntry,obstacleEntry){
    if(obstacleEntry.id===textEntry.containerId)return true;
    for(var i=0;i<textEntry.allowedOverlapIds.length;i++)if(textEntry.allowedOverlapIds[i]===obstacleEntry.id)return true;
    for(var j=0;j<obstacleEntry.allowedOverlapIds.length;j++)if(obstacleEntry.allowedOverlapIds[j]===textEntry.id)return true;
    return !!(textEntry.layoutGroup&&textEntry.layoutGroup===obstacleEntry.layoutGroup&&obstacleEntry.role==='frame');
  }
  function collidesWithGraphic(resolvedItem){var tb=bounds(resolvedItem.text);for(var i=0;i<obstacleItems.length;i++){var o=obstacleItems[i];if(!overlapAllowed(resolvedItem.entry,o.entry)&&graphicHits(tb,o.item,o.entry.role))return o;}return null;}
  function textOverlapAllowed(first,second){
    for(var i=0;i<first.allowedOverlapIds.length;i++)if(first.allowedOverlapIds[i]===second.id)return true;
    for(var j=0;j<second.allowedOverlapIds.length;j++)if(second.allowedOverlapIds[j]===first.id)return true;
    return false;
  }
  function collidesWithText(resolvedItem){var tb=bounds(resolvedItem.text);for(var i=0;i<resolved.length;i++){var other=resolved[i];if(other===resolvedItem||textOverlapAllowed(resolvedItem.entry,other.entry))continue;if(intersects(tb,bounds(other.text)))return other;}return null;}
  for(var cr=0;cr<resolved.length;cr+=1){
    var candidate=resolved[cr],collision=collidesWithGraphic(candidate),textCollision=collidesWithText(candidate);
    var isSingleBoxed=candidate.box!==null&&groups[candidate.entry.containerObjectName].length===1;
    var isFreeLabel=candidate.box===null&&!candidate.entry.containerObjectName;
    if((collision!==null||textCollision!==null)&&c.repairText&&(isSingleBoxed||isFreeLabel)){
      var step=Math.max(2,Number(candidate.text.textRange.characterAttributes.size)*0.5),moved=false;
      var directions=[[0,1],[0,-1],[1,0],[-1,0],[1,1],[-1,1],[1,-1],[-1,-1]];
      var artboard=app.activeDocument.artboards[app.activeDocument.artboards.getActiveArtboardIndex()].artboardRect;
      for(var ring=1;ring<=6&&!moved;ring+=1){for(var di=0;di<directions.length;di+=1){
        var dx=directions[di][0]*step*ring,dy=directions[di][1]*step*ring;candidate.text.translate(dx,dy);
        var cb=bounds(candidate.text),insideArtboard=cb.l>=artboard[0]+2&&cb.r<=artboard[2]-2&&cb.t<=artboard[1]-2&&cb.b>=artboard[3]+2;
        var insideOwner=isFreeLabel||fits(candidate.text,candidate.box,Number(candidate.text.textRange.characterAttributes.size)*Number(candidate.entry.paddingMultiple));
        if(insideArtboard&&insideOwner&&collidesWithGraphic(candidate)===null&&collidesWithText(candidate)===null){repairCount+=1;moved=true;break;}candidate.text.translate(-dx,-dy);
      }}
      if(!moved&&isFreeLabel){
        var originalSize=Number(candidate.text.textRange.characterAttributes.size),trialSize=originalSize,freeFloor=Math.max(8,originalSize*0.75);
        while(trialSize-0.5>=freeFloor&&!moved){
          trialSize-=0.5;candidate.text.textRange.characterAttributes.size=trialSize;
          if(collidesWithGraphic(candidate)===null&&collidesWithText(candidate)===null){repairCount+=1;moved=true;break;}
          for(var shrinkRing=1;shrinkRing<=6&&!moved;shrinkRing+=1){for(var shrinkDirection=0;shrinkDirection<directions.length;shrinkDirection+=1){
            var sdx=directions[shrinkDirection][0]*Math.max(2,trialSize*0.5)*shrinkRing,sdy=directions[shrinkDirection][1]*Math.max(2,trialSize*0.5)*shrinkRing;candidate.text.translate(sdx,sdy);
            var sb=bounds(candidate.text),sInside=sb.l>=artboard[0]+2&&sb.r<=artboard[2]-2&&sb.t<=artboard[1]-2&&sb.b>=artboard[3]+2;
            if(sInside&&collidesWithGraphic(candidate)===null&&collidesWithText(candidate)===null){repairCount+=1;moved=true;break;}candidate.text.translate(-sdx,-sdy);
          }}
        }
        if(!moved)candidate.text.textRange.characterAttributes.size=originalSize;
      }
      collision=collidesWithGraphic(candidate);
      textCollision=collidesWithText(candidate);
    }
    if(collision!==null)issues.push('TEXT_GRAPHIC_OVERLAP:'+candidate.entry.id+':'+collision.entry.id);
  }
  for(var a=0;a<c.entries.length;a+=1){
    var first=findNamed(root,c.entries[a].objectName);if(first===null)continue;var fb=bounds(first);
    for(var z=a+1;z<c.entries.length;z+=1){
      var allowed=false;
      for(var q=0;q<c.entries[a].allowedOverlapIds.length;q+=1)if(c.entries[a].allowedOverlapIds[q]===c.entries[z].id)allowed=true;
      for(var w=0;w<c.entries[z].allowedOverlapIds.length;w+=1)if(c.entries[z].allowedOverlapIds[w]===c.entries[a].id)allowed=true;
      if(allowed)continue;
      var second=findNamed(root,c.entries[z].objectName);if(second===null)continue;var sb=bounds(second);
      var iw=Math.min(fb.r,sb.r)-Math.max(fb.l,sb.l),ih=Math.min(fb.t,sb.t)-Math.max(fb.b,sb.b);
      if(iw>0.5&&ih>0.5)issues.push('TEXT_TEXT_OVERLAP:'+c.entries[a].id+':'+c.entries[z].id);
    }
  }
  return (issues.length?'FAIL':'PASS')+'|repairs='+repairCount+'|issues='+issues.join(',');
}());
"@

$result = [string]$Illustrator.DoJavaScript($script)
if ($result.StartsWith('ERROR|')) { throw $result }
$parts = $result -split '\|'
$status = $parts[0]
$repairCount = 0
$issueValues = @()
foreach ($part in $parts[1..($parts.Count - 1)]) {
    if ($part.StartsWith('repairs=')) { $repairCount = [int]$part.Substring(8) }
    if ($part.StartsWith('issues=')) {
        $rawIssues = $part.Substring(7)
        if (-not [string]::IsNullOrWhiteSpace($rawIssues)) { $issueValues = @($rawIssues -split ',') }
    }
}
$report = [ordered]@{
    schema_version = '1.0'
    status = $status
    root_group_name = $RootGroupName
    cache_path = $cacheFile
    approved_svg = $svgFile
    checked_text_count = $entries.Count
    repair_count = $repairCount
    unresolved_count = $issueValues.Count
    issues = $issueValues
    diagnostics = @($issueValues | ForEach-Object { ConvertTo-CellLctLayoutDiagnostic -Issue $_ })
}
$reportDirectory = Split-Path -Parent $reportFile
if ($reportDirectory) { New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null }
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportFile -Encoding UTF8
Write-Output ("LAYOUT_POSTFLIGHT|status={0}|repairs={1}|unresolved={2}|report={3}" -f $status, $repairCount, $issueValues.Count, $reportFile)
if ($status -ne 'PASS') { exit 2 }
