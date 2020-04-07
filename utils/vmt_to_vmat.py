# Converts Source 1 .vmt material files to simple Source 2 .vmat files.
#
# Copyright (c) 2016 Rectus
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Usage Instructions:
# Place all vmts and vtfs in their proper folder structure up till "materials"
# (we'd recomend you just drop it in the content folder for ease of use)
# Using VTFCmd or VTFEdit, use Tools->Convert Folder and convert your entire .vtf folder to .tgas
# cmd: python vmt_to_vmat.py PATH
# i.e.: python vmt_to_vmat.py "C:\Program Files (x86)\Steam\steamapps\common\Half-Life Alyx\content\hl2\materials\models\alyx"
# OR
# i.e.: python vmt_to_vmat.py "C:\Program Files (x86)\Steam\steamapps\common\Half-Life Alyx\content\hl2\materials\models\alyx\alyx_faceandhair.vmt"

import sys
import os
import os.path
from os import path
import re

from PIL import Image
import PIL.ImageOps

import numpy as np
from blend_modes import blending_functions

#from VTFLibWrapper.VTFLibEnums import ImageFlag
#from VTFLibWrapper import VTFLib
#from VTFLibWrapper import VTFLibEnums
#vtf_lib = VTFLib.VTFLib()

# What shader to use.
SHADER = 'vr_standard'
# File format of the textures.
TEXTURE_FILEEXT = '.tga'
# Set this to True if you wish to overwrite your old vmat files
OVERWRITE_VMAT = True
# For some reason, VR Complex doesn't have proper pbr support (as in no support for reflectivity maps or glossiness)
# Because of this, we are just hacking so when compiling for VR_Complex, we set this to true
PBR_HACK = False
# A lot of looks for Source games seem to hinge on Reflectance Range being correct, so for now, we're making
# a seperate variable for it to make it easier to modify on a per-game basis. HL2 seems to be 0.5
reflRange = 0.5

filePath = sys.argv[1]
modPath = ""

# material types need to be lowercase because python is a bit case sensitive
# TODO: later, we will convert these to be in a dictionary with the following format
# "shaderName": ("HLATargetShader", "SVRHTargetShader", "DOTATargetShader"),
# We will also have a flag for HLA, SVRH (steamtours), and DOTA)
# For now though, just pretend everything uses TextureColor and fuck everything else
vmtSupportedShaders = [
"vertexlitgeneric",         # + Convert to VR Complex
"unlitgeneric",             # TODO: Convert to VR Complex, selfIllum with white mask
"unlittwotexture",          # TODO: Vr Simple 2layer Parallax?
"patch",                    # TODO: ughhhhhhhhhhhhhhhhhhhhhhhhh
"teeth",                    # + Convert to VR Complex
"eyes",                     # + Convert to VR Complex
"eyeball",                  # + Convert to VR Complex
"eyerefract",               # + Convert to VR Complex
"modulate",                 # TODO: Refract/Glass Shader?
"water",                    # TODO: Ditto
"refract",                  # TODO: Ditto
"worldvertextransition",    # TODO: Vr Simple 2way Blend
"lightmappedgeneric",       # + Convert to VR Complex
"lightmapped_4wayblend",    # TODO: 4 Way Blend. No good shader for this, maybe just Vr Simple 2way Blend?
"multiblend",               # TODO: Ditto
"hero",                     # TODO: DOTA Shader: to be worked on for compatibility
"lightmappedtwotexture",    # TODO: Vr Simple 2layer Parallax?
"lightmappedreflective",    # + Convert to VR Complex
"decalmodulate",            # TODO: See if this needs extra work
"cables"                    # TODO: Find appropriate shader or maybe just vr_complex?
]
ignoreList = [
"vertexlitgeneric_hdr_dx9",
"vertexlitgeneric_dx9",
"vertexlitgeneric_dx8",
"vertexlitgeneric_dx7",
"lightmappedgeneric_hdr_dx9",
"lightmappedgeneric_dx9",
"lightmappedgeneric_dx8",
"lightmappedgeneric_dx7",
]

###
### Classes
###
class RGBAImage:
    r = None
    g = None
    b = None
    a = None

    def __init__(self, size, col):
        self.r,self.g,self.b,self.a = Image.new("RGBA", size, col).split()

    def resizeAll(self, newSize):
        self.r = self.r.resize(newSize)
        self.g = self.g.resize(newSize)
        self.b = self.b.resize(newSize)
        self.a = self.a.resize(newSize)

    def setRG(self, image, flip = False):
        self.r.resize(image.size)
        self.g.resize(image.size)
        if (flip):
            self.r = PIL.ImageOps.invert(image)
            self.g = PIL.ImageOps.invert(image)
        else:
            self.r = image
            self.g = image

    def setRGB(self, image, flip = False):
        self.r.resize(image.size)
        self.g.resize(image.size)
        self.b.resize(image.size)

        if(flip):
            self.r = PIL.ImageOps.invert(image)
            self.g = PIL.ImageOps.invert(image)
            self.b = PIL.ImageOps.invert(image)
        else:
            self.r = image
            self.g = image
            self.b = image

    def setRGBA(self, image, flip = False):
        self.r.resize(image.size)
        self.g.resize(image.size)
        self.b.resize(image.size)
        self.a.resize(image.size)

        if(flip):
            self.r = PIL.ImageOps.invert(image)
            self.g = PIL.ImageOps.invert(image)
            self.b = PIL.ImageOps.invert(image)
            self.a = PIL.ImageOps.invert(image)
        else:
            self.r = image
            self.g = image
            self.b = image
            self.a = image

    def saveFile(self, filePath):
        imageOut = Image.merge('RGBA', (self.r, self.g, self.b, self.a))
        imageOut.save(filePath)
        imageOut.close()

###
### Small Functions
###

def parseDir(dirName):
    files = []
    for root, dirs, fileNames in os.walk(dirName):
        for fileName in fileNames:
            if fileName.lower().endswith('.vmt'):
                files.append(os.path.join(root,fileName))

    return files

def parseLine(inputString):
    inputString = inputString.lower().replace('"', '').replace("'", "").replace("\n", "").replace("\t", "")
    return inputString

def fixTexturePath(p, addonString = ""):
    retPath = p.strip().strip('"')
    retPath = retPath.replace('\\', '/') # Convert paths to use forward slashes.
    retPath = retPath.replace('.vtf', '') # remove any old extensions
    retPath = '"materials/' + retPath + addonString + TEXTURE_FILEEXT + '"'
    return retPath

def fixVector(s, divVar = 1):
    s = s.strip('"][}{ ') # some VMT vectors use {}
    parts = [str(float(i) / divVar) for i in s.split(' ')]
    extra = (' 0.0' * max(3 - s.count(' '), 0) )
    return '"[' + ' '.join(parts) + extra + ']"'

def vectorToArray(s, divVar = 1):
    s = s.strip('"][}{ ') # some VMT vectors use {}
    parts = [float(i) / divVar for i in s.split(' ')]
    #extra = (' 0.0' * max(3 - s.count(' '), 0) )
    return parts

def text_parser(filepath, separator="="):
    return_dict = {}
    with open(filepath, "r") as f:
        for line in f:
            if not line.startswith("//"):
                line = line.replace('\t', '').replace('\n', '')
                line = line.split(separator)
                return_dict[line[0]] = line[1]
    return return_dict

###
### Big Functions
###
def parseVMTParameter(line, parameters):
    words = []

    if line.startswith('\t') or line.startswith(' '):
        words = re.split(r'\s+', line, 2)
    else:
        words = re.split(r'\s+', line, 1)

    words = list(filter(len, words))
    if len(words) < 2:
        return

    key = words[0].strip('"').lower() # we process all values and keys as lowercase

    if key.startswith('/'):
        return

    if not key.startswith('$'):
        if not key.startswith('include'):
            return

    val = words[1].strip('\n').lower() # we process all values and keys as lowercase

    commentTuple = val.partition('//')

    if(val.strip('"' + "'") == ""):
        print("+ No value found, moving on")
        return

    if not commentTuple[0] in parameters:
        parameters[key] = commentTuple[0].replace("'", "").replace('"', '').replace("\n", "").replace("\t", "")
        # reports back as dict with the format $basetexture models/alyx/alyx_faceandhair

def getVmatParameter(key, val):
    key = key.strip('$').lower()

    # Dict for converting parameters
    convert = {
        #VMT paramter: VMAT parameter, value, additional lines to add. The last two variables take functions or strings, or None for using the old value.
        'basetexture': ('TextureColor', fixTexturePath, None),
        'basetexture2': ('TextureLayer1Color', fixTexturePath, None),
        'bumpmap': ('TextureNormal', fixTexturePath, None),
        'normalmap': ('TextureNormal', fixTexturePath, None),
        'envmap': ('F_SPECULAR', '1', '\tF_SPECULAR_CUBE_MAP 1\n\tF_SPECULAR_CUBE_MAP_PROJECTION 1\n\tg_flCubeMapBlurAmount "1.000"\n\tg_flCubeMapScalar "1.000"\n'), #Assumes env_cubemap
        #'envmaptint': ('TextureReflectance', fixVector, None),
        'envmapmask': ('TextureReflectance', fixTexturePath, None),
        'color': ('g_vColorTint', None, None), #Assumes being used with basetexture
        'selfillum': ('g_flSelfIllumScale', '"1.000"', None),
        'selfillumtint': ('g_vSelfIllumTint', None, None),
        'selfillummask': ('TextureSelfIllumMask', fixTexturePath, None),
        'phongexponenttexture': ('TextureGlossiness', fixTexturePath, None),
        'translucent': ('F_TRANSLUCENT', None, '\tg_flOpacityScale "1.000"\n'),
        'additive': ('F_ADDITIVE_BLEND', None, None),
        'nocull': ('F_RENDER_BACKFACES', None, None),
        'decal':( 'F_OVERLAY', None, None),
		}

    if key in convert:
        outValue = val
        additionalLines = ''

        if isinstance(convert[key][1], str):
            outValue = convert[key][1]
        elif hasattr(convert[key][1], '__call__'):
            outValue = convert[key][1](val)

        if isinstance(convert[key][2], str):
            additionalLines = convert[key][2]
        elif hasattr(convert[key][2], '__call__'):
            additionalLines = convert[key][2](val)

        '''if isinstance(convert[key][3], bool):
            if(val.replace('"', '') == "0" or val.replace('"', '') == "false"):
                return ''
        elif hasattr(convert[key][3], '__call__'):
            print("Error: no bool at the end of dict!!")
            return ''
            '''

        return '\t' + convert[key][0] + ' ' + outValue + '\n' + additionalLines

    return ''

###
### Main Execution
###

print('--------------------------------------------------------------------------------------------------------\nSource 2 Material Conveter! By Rectus via Github.\nInitially forked by Alpyne, this version by caseytube.\n--------------------------------------------------------------------------------------------------------')

# Verify file paths
fileList = []

# HACK; See note under PBR_HACK
if SHADER.lower() == "vr_complex":
    PBR_HACK = True

if(len(sys.argv) == 2):
    absFilePath = os.path.abspath(filePath)
    if os.path.isdir(absFilePath):
        fileList.extend(parseDir(absFilePath))
    elif(absFilePath.lower().endswith('.vmt')):
        fileList.append(absFilePath)
    else:
        print("ERROR: File path is invalid. required format: vmt_to_vmat.py C:\optional\path\to\root")
        quit()
else:
    print("ERROR: CMD Arguments are invalid. Required format: vmt_to_vmat.py C:\optional\path\to\root")
    quit()

for fileName in fileList:
    print("+ Processing .vmt file: " + fileName)
    baseFileName  = os.path.basename(fileName.replace('.vmt', ''))
    if modPath == "":
        modPath = fileName.split('materials')[0]
    vmtParameters = {}
    vmtShader = ""

    with open(fileName, 'r') as vmtFile:
        for line in vmtFile.readlines():
            if parseLine(line) in vmtSupportedShaders:
                vmtShader = parseLine(line)
            else:
                parseVMTParameter(line, vmtParameters)

        if vmtShader == "": # vmt shader not supported
            print("- Unsupported shader in " + baseFileName + ". Skipping!")
            continue #skip!

    texColor = RGBAImage((8, 8), (0,0,0,255))
    texNormal = RGBAImage((8, 8), (0,0,0,255))
    texRough = RGBAImage((8, 8), (0,0,0,255))
    texAo = RGBAImage((8, 8), (0,0,0,255))
    texSelfIllum = RGBAImage((8, 8), (0,0,0,255))
    texMetal = RGBAImage((8, 8), (0,0,0,255))
    texTrans = RGBAImage((8, 8), (0,0,0,255))
    texDetail = RGBAImage((8, 8), (0, 0, 0, 255))
    # not used by VR Complex for some reason, but we're keeping it here for legacy support
    texRefl = RGBAImage((8, 8), (0,0,0,255))
    texGloss = RGBAImage((8, 8), (0, 0, 0, 255))

    vmatFileName = fileName.replace('.vmt', '') + '.vmat'
    if os.path.exists(vmatFileName) and not OVERWRITE_VMAT:
            print('+ File already exists. Skipping!')
            continue

    print('+ Creating ' + os.path.basename(vmatFileName))
    with open(vmatFileName, 'w') as vmatFile:
        vmatFile.write('// Converted with vmt_to_vmat.py\n\n')
        vmatFile.write('Layer0\n{\n\tshader "' + SHADER + '.vfx"\n\n')

        # Prep TextureColor
        if "$basetexture" in vmtParameters:

            tgaPath = modPath + "materials\\" + vmtParameters["$basetexture"] + ".tga"

            baseTex = RGBAImage((8, 8), (0,0,0,255))
            try:
                baseTexture = Image.open(tgaPath)
            except:
                print("- ERROR: .tga file " + tgaPath + " does not exist. Ending texture conversion early.")
                vmatFile.write('}\n')
                continue

            baseTex.r,baseTex.g,baseTex.b,baseTex.a = baseTexture.split()
            baseTexture.close()
            texSize = baseTex.a.size

            texColor.resizeAll(texSize)
            texColor = baseTex

            if "$basemapalphaphongmask" in vmtParameters:
                texRough.resizeAll(texSize)
                texRough.r = PIL.ImageOps.invert(baseTex.a)
                texRough.g = PIL.ImageOps.invert(baseTex.a)
                texRough.b = PIL.ImageOps.invert(baseTex.a)

            if "$selfillum" in vmtParameters and "$selfillummask" not in vmtParameters:
                texSelfIllum.resizeAll(texSize)
                texSelfIllum.setRGBA(baseTex.a)

            if "$translucent" in vmtParameters or "$alphatest" in vmtParameters:
                texTrans.resizeAll(texSize)
                texTrans.setRGBA(baseTex.a)

            if "$basealphaenvmapmask" in vmtParameters:
                texRefl.resizeAll(texSize)
                texRefl.setRGBA(baseTex.a, True)

            if "$color" in vmtParameters:
                if "{" in vmtParameters["$color"]:
                    vmatFile.write('\tg_vColorTint ' + fixVector(vmtParameters["$color"], 255) + '\n') #process as int
                elif "[" in vmtParameters["$color"]:
                    vmatFile.write('\tg_vColorTint ' + fixVector(vmtParameters["$color"]) + '\n') #process as float
            elif "$color2" in vmtParameters:
                if "{" in vmtParameters["$color2"]:
                    vmatFile.write('\tg_vColorTint ' + fixVector(vmtParameters["$color2"], 255) + '\n') #process as int
                elif "[" in vmtParameters["$color2"]:
                    vmatFile.write('\tg_vColorTint ' + fixVector(vmtParameters["$color2"]) + '\n') #process as float

            texColor.saveFile(fileName.replace('.vmt', '_color.tga'))
            vmatFile.write('\tTextureColor "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_color.tga') + '"\n')

        # Prep TextureNormal for normal/bump maps
        if "$bumpmap" in vmtParameters or "$normalmap" in vmtParameters:
            if "$bumpmap" in vmtParameters:
                tgaPath = modPath + "materials\\" + vmtParameters["$bumpmap"] + ".tga"
            elif "$normalmap" in vmtParameters:
                tgaPath = modPath + "materials\\" + vmtParameters["$normalmap"] + ".tga"

            bumpTex = RGBAImage((8, 8), (0,0,0,255))
            try:
                bumpTexture = Image.open(tgaPath)
            except:
                print("- ERROR: .tga file " + tgaPath + " does not exist. Ending texture conversion early.")
                vmatFile.write('}\n')
                continue
            bumpTex.r,bumpTex.g,bumpTex.b,bumpTex.a = bumpTexture.split()
            bumpTexture.close()
            texSize = bumpTex.a.size

            texNormal.resizeAll(texSize)
            texNormal = bumpTex

            if "$basemapalphaphongmask" not in vmtParameters:
                texRough.resizeAll(texSize)
                texRough.r = PIL.ImageOps.invert(bumpTex.a)
                texRough.g = PIL.ImageOps.invert(bumpTex.a)
                texRough.b = PIL.ImageOps.invert(bumpTex.a)

            if "$normalmapalphaenvmapmask" in vmtParameters:
                texRefl.resizeAll(texSize)
                texRefl.setRGBA(bumpTex.a, False) # for some reason, normal map env masks seem reversed. HACKing for now

            texNormal.saveFile(fileName.replace('.vmt', '_normal.tga'))
            # For normal maps, we produce a file called fileName.txt that tells Source 2 to flip the green channel
            bumpSettingsFileName = fileName.replace(".vmt", "_normal.txt")
            with open(bumpSettingsFileName, 'w') as bumpSettings:
                bumpSettings.write('"settings"\n'
                                   '{\n'
                                   '\t"legacy_source1_inverted_normal"\t"1"\n'
                                   '}')

            vmatFile.write('\tTextureNormal "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_normal.tga') + '"\n')

        # Prep TextureRoughness using phongmask details
        if "$envmap" in vmtParameters:
            vmatFile.write('\tF_SPECULAR 1\n')

        if "$phong" in vmtParameters and vmtParameters["$phong"] == "1":
            vmatFile.write('\tF_SPECULAR 1\n')
            vmatFile.write('\tg_vReflectanceRange "[0.000 ' + str(reflRange) + ']"\n')  # Sets the default "phong" value if none else available.

        # HACK
        if texRough.r.size != (8, 8):
            vmatFile.write('\tTextureRoughness "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_rough.tga') + '"\n')
            texRough.saveFile(fileName.replace('.vmt', '_rough.tga'))

        # This is a major HACK. Currently I don't know of any analogs for these commands, and
        # the properties of their envmap masks cause severe headaches and bad looking models.
        # My solution is to set metalness to 1.0 for models that take these commands. This is
        # definately wrong, but it's doing well so far.
        envMaskProblematicCommands = {
            #"$envmapfresnel",
            #"$envmapsaturation",
            #"$envmapcontrast"
        }
        # Prep Reflectivity Map using Envmask
        # TODO: Add functionality for all the weird envmap mask stuff
        if "$envmap" in vmtParameters and not any(props in vmtParameters for props in envMaskProblematicCommands):
            if "$envmapmask" in vmtParameters:
                envmapTGA = modPath + "materials\\" + vmtParameters["$envmapmask"] + ".tga"

                envTex = RGBAImage((8, 8), (0,0,0,255))
                try:
                    envTexture = Image.open(envmapTGA)
                    print(envmapTGA)
                except:
                    print("- ERROR: .tga file " + envmapTGA + " does not exist. Ending texture conversion early.")
                    vmatFile.write('}\n')
                    continue
                envTex.r,envTex.g,envTex.b,envTex.a = envTexture.split()
                envTexture.close()
                texSize = envTex.a.size

                texRefl.resizeAll(texSize)

                #texRefl.setRGBA(envTex.r, True)
                texRefl.r = envTex.r
                texRefl.g = envTex.g
                texRefl.b = envTex.b
                texRefl.a = envTex.a

                if "$selfillum_envmapmask_alpha" in vmtParameters:
                    texSelfIllum.resizeAll(texSize)
                    texSelfIllum.setRGBA(envTex.a)

            # HACK: Lots of things here that feel like hacks. Need to clean this up more. It's slowing the script down a ton.
            tempEnv = Image.merge("RGBA", (texRefl.r, texRefl.g, texRefl.b, texRefl.a))
            if "$envmapcontrast" in vmtParameters:
                blendedTex = np.array(tempEnv)
                blendedTex_float = blendedTex.astype(float)
                opacity = float(vmtParameters["$envmapcontrast"])
                blendedTex_float = blending_functions.multiply(blendedTex_float, blendedTex_float, opacity)
                blendedTex = np.uint8(blendedTex_float)
                tempEnv = Image.fromarray(blendedTex)

            texRefl.r, texRefl.g, texRefl.b, texRefl.a = tempEnv.split()

            # $envmaptint was used to tint the color of the envmap reflection. alternatively, it was also used to water down the
            # effect of the reflection. so in this case, since S2 doesn't support tinted cubemaps, we are interpreting it as
            # a flat number to be blended with the envmap, so that reflections look closer to their S2 counterparts when
            # watered down.
            tintAvg = 1
            if "$envmaptint" in vmtParameters:
                if "{" in vmtParameters["$envmaptint"]:
                    envTint = vectorToArray(vmtParameters["$envmaptint"], 255)
                else:
                    envTint = vectorToArray(vmtParameters["$envmaptint"])

                tintAvg = sum(envTint) / len(envTint)

            vmatFile.write('\tg_vReflectanceRange "[0.000 ' + str(tintAvg * reflRange) + ']"\n')

            if not PBR_HACK:
                vmatFile.write('\tF_SPECULAR_CUBE_MAP 1\n')
                vmatFile.write('\tTextureReflectance "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_refl.tga') + '"\n')

                texRefl.saveFile(fileName.replace('.vmt', '_refl.tga'))

        '''if "$surfaceprop" in vmtParameters:
            if "metal" in vmtParameters["$surfaceprop"]:
                vmatFile.write('\tg_flMetalness "1.000"\n')'''

        # Prep Glossiness Map using Phong Exponent
        if "$phongexponenttexture" in vmtParameters and "$phongexponent" not in vmtParameters:
            phongExpTGA = modPath + "materials\\" + vmtParameters["$phongexponenttexture"] + ".tga"

            phongTex = RGBAImage((8, 8), (0, 0, 0, 255))
            try:
                phongTexture = Image.open(phongExpTGA)
            except:
                print("- ERROR: .tga file " + phongExpTGA + " does not exist. Ending texture conversion early.")
                vmatFile.write('}\n')
                continue
            phongTex.r, phongTex.g, phongTex.b, phongTex.a = phongTexture.split()
            phongTexture.close()
            texGloss.resizeAll(phongTex.r.size)

            texGloss.r = phongTex.r
            texGloss.g = phongTex.g
            texGloss.b = phongTex.b
            texGloss.a = phongTex.a

            if not PBR_HACK:
                vmatFile.write('\tTextureGlossiness "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_gloss.tga') + '"\n')
                texGloss.saveFile(fileName.replace('.vmt', '_gloss.tga'))
        elif "$phongexponent" in vmtParameters:
            specValue2 = vmtParameters["$phongexponent"]
            specValue = float(specValue2)/150
            vmatFile.write('\tTextureGlossiness "[' + str(specValue) + ' ' + str(specValue) + ' ' + str(specValue) + ' 0.000]"\n')
            #texGloss.saveFile(fileName.replace('.vmt', '_gloss.tga'))
        elif "$phong" in vmtParameters and "$phongexponent" not in vmtParameters and "$phongexponenttexture" not in vmtParameters:
            vmatFile.write('\tTextureGlossiness "[0.033000 0.033000 0.033000 0.000000]"\n')
            #texGloss.saveFile(fileName.replace('.vmt', '_gloss.tga'))

        # Prep TextureSelfIllum using selfillum stuff
        if "$selfillum" in vmtParameters:
            if "$selfillummask" in vmtParameters:
                tgaPath = modPath + "materials\\" + vmtParameters["$selfillummask"] + ".tga"
                illumTex = RGBAImage((8, 8), (0,0,0,255))
                try:
                    illumTexture = Image.open(tgaPath)
                except:
                    print("- ERROR: .tga file " + tgaPath + " does not exist. Ending texture conversion early.")
                    vmatFile.write('}\n')
                    continue
                illumTex.r,illumTex.g,illumTex.b,illumTex.a = illumTexture.split()
                illumTexture.close()
                texSize = illumTex.r.size

                texSelfIllum.resizeAll(texSize)
                texSelfIllum.r = illumTex.r
                texSelfIllum.g = illumTex.g
                texSelfIllum.b = illumTex.b

            vmatFile.write('\tF_SELF_ILLUM 1\n')
            vmatFile.write('\tTextureSelfIllumMask "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_selfillum.tga') + '"\n')
            if "$selfillumtint" in vmtParameters:
                vmatFile.write('\tg_vSelfIllumTint ' + fixVector(vmtParameters["$selfillumtint"]) + '\n')
            if "$selfillummaskscale" in vmtParameters:
                vmatFile.write('\tg_flSelfIllumScale "' + vmtParameters['$selfillummaskscale'] + '"\n')
            texSelfIllum.saveFile(fileName.replace('.vmt', '_selfillum.tga'))

        # Prep Details stuff
        if "$detail" in vmtParameters:
            vmatFile.write('\tTextureDetail "' + 'materials/' + vmtParameters["$detail"].replace('.vtf', '') + '.tga"\n')
            if "$detailblendmode" in vmtParameters and vmtParameters["$detailblendmode"] == "1":
                vmatFile.write('\tF_DETAIL_TEXTURE 2\n') # Overlay
            else:
                vmatFile.write('\tF_DETAIL_TEXTURE 1\n') # Mod2X
            if "$detailscale" in vmtParameters:
                vmatFile.write('\tg_vDetailTexCoordScale "[' + vmtParameters["$detailscale"] + ' ' + vmtParameters["$detailscale"] + ']"\n')
            if "$detailblendfactor" in vmtParameters:
                vmatFile.write('\tg_flDetailBlendFactor "' + vmtParameters["$detailblendfactor"] + '"\n')

        # Prep TextureTransparancy using either alphatest or translucent
        if "$translucent" in vmtParameters or "$alphatest" in vmtParameters:
            if "$translucent" in vmtParameters:
                vmatFile.write('\tF_TRANSLUCENT 1\n')
            elif "$alphatest" in vmtParameters:
                vmatFile.write('\tF_ALPHA_TEST 1\n')
            if "$additive" in vmtParameters:
                vmatFile.write('\tF_ADDITIVE_BLEND 1\n')
            vmatFile.write('\tTextureTranslucency "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_trans.tga') + '"\n')
            texTrans.saveFile(fileName.replace('.vmt', '_trans.tga'))

        # Rarely used, but ambient occlusion maps are sometimes available
        if "$ambientoccltexture" in vmtParameters or "$ambientocclusiontexture" in vmtParameters:
            if "$ambientoccltexture" in vmtParameters:
                tgaPath = modPath + "materials\\" + vmtParameters["$ambientoccltexture"] + ".tga"
            elif "$ambientocclusiontexture" in vmtParameters:
                tgaPath = modPath + "materials\\" + vmtParameters["$ambientocclusiontexture"] + ".tga"

            aoTex = RGBAImage((8, 8), (0,0,0,255))
            try:
                aoTexture = Image.open(tgaPath)
            except:
                print("- ERROR: .tga file " + tgaPath + " does not exist. Ending texture conversion early.")
                vmatFile.write('}\n')
                continue
            aoTex.r,aoTex.g,aoTex.b,aoTex.a = aoTexture.split()
            aoTexture.close()
            texSize = aoTex.a.size

            texAo.resizeAll(texSize)
            texAo = aoTex

            texAo.saveFile(fileName.replace('.vmt', '_ao.tga'))
            vmatFile.write('\tTextureAmbientOcclusion "' + 'materials' + fileName.split('materials')[1].replace('.vmt', '_ao.tga') + '"\n')

        vmatFile.write('}\n')

    print('+ Finished Writing ' + vmatFileName)

    '''
    if "$basetexture" in vmtParameters:
        vtfPath = modPath + "materials\\" + vmtParameters["$basetexture"] + ".vtf"
        #if os.path.exists(vtfPath):
        vtf_lib.image_load(vtfPath)
        if vtf_lib.image_is_loaded():
            print('Image loaded successfully')
            
            rgba_data = vtf_lib.convert_to_rgba8888()
            pixels = np.array(rgba_data.contents, np.uint8)
            pixels = pixels.astype(np.uint8, copy=False)
            
            #testImage = Image.new("RGBA", (vtf_lib.width(), vtf_lib.height()))
            print (pixels.size)
            pixels = Image.fromarray(pixels, "RGBA")
            pixels.save(baseFileName + "_color.tga")
            print(pixels)
            #texColor = rgba_data
            #texColor.save(baseFileName + "_color.tga")'''
    '''texColor.save(os.path.basename(fileName.replace('.vmt', '')) + "_color.tga")
    texNormal.save(os.path.basename(fileName.replace('.vmt', '')) + "_normal.tga")
    texRough.save(os.path.basename(fileName.replace('.vmt', '')) + "_rough.tga")
    texAo.save(os.path.basename(fileName.replace('.vmt', '')) + "_ao.tga")
    texSelfIllum.save(os.path.basename(fileName.replace('.vmt', '')) + "_selfIllum.tga")
    texMetal.save(os.path.basename(fileName.replace('.vmt', '')) + "_metal.tga")
    texTrans.save(os.path.basename(fileName.replace('.vmt', '')) + "_trans.tga")
    texRefl.save(os.path.basename(fileName.replace('.vmt', '')) + "_refl.tga")
    texDetail.save(os.path.basename(fileName.replace('.vmt', '')) + "_detail.tga")'''

