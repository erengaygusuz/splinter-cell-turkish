/******************************************************************************
 Class:         EGameplaySubtitleTracker

 Description:   Audio-synchronized gameplay subtitle tracker. This class is
                deliberately non-native so its fields cannot alter the native
                EchelonMainHUD layout expected by EchelonHUD.dll.
******************************************************************************/

class EGameplaySubtitleTracker extends Actor;

var Sound TrainingOpeningSounds[17];
var bool bTrainingOpeningSoundsLoaded;

function PostBeginPlay()
{
	Super.PostBeginPlay();

	if (InStr(Caps(Level.GetLocalURL()), "0_0_2_TRAINING") == -1)
		return;

	TrainingOpeningSounds[0]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_01", class'Sound'));
	TrainingOpeningSounds[1]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_02", class'Sound'));
	TrainingOpeningSounds[2]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_03", class'Sound'));
	TrainingOpeningSounds[3]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_04", class'Sound'));
	TrainingOpeningSounds[4]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_05", class'Sound'));
	TrainingOpeningSounds[5]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_08", class'Sound'));
	TrainingOpeningSounds[6]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_09", class'Sound'));
	TrainingOpeningSounds[7]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_10", class'Sound'));
	TrainingOpeningSounds[8]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_11", class'Sound'));
	TrainingOpeningSounds[9]  = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_12", class'Sound'));
	TrainingOpeningSounds[10] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_13", class'Sound'));
	TrainingOpeningSounds[11] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_14", class'Sound'));
	TrainingOpeningSounds[12] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_15", class'Sound'));
	TrainingOpeningSounds[13] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_16", class'Sound'));
	TrainingOpeningSounds[14] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_17", class'Sound'));
	TrainingOpeningSounds[15] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_18", class'Sound'));
	TrainingOpeningSounds[16] = Sound(DynamicLoadObject("S0_0_2Voice.Play_00_15_19", class'Sound'));

	bTrainingOpeningSoundsLoaded = true;
}

function string GetCurrentSubtitle()
{
	local int i;
	local string LocalizationKey;

	if (!bTrainingOpeningSoundsLoaded)
		return "";

	for (i = 0; i < 17; i++)
	{
		if (TrainingOpeningSounds[i] != None && IsPlayingAnyActor(TrainingOpeningSounds[i]))
		{
			if (i == 0)
				LocalizationKey = "Speech_0001L";
			else if (i == 1)
				LocalizationKey = "Speech_0002L";
			else
				LocalizationKey = "Speech_" $ Right("0000" $ string(i + 2), 4) $ "L";

			return Localize(
				"P_0_0_2_Training_ScriptedEvents",
				LocalizationKey,
				"Localization\\P_0_0_2_Training");
		}
	}

	return "";
}

defaultproperties
{
	bHidden=True
}
