from app import clone_planner, raghu_pipeline


def test_character_only_speaks_the_direct_hindi_line():
    line = clone_planner.Line(text="उसने बेटे को डाँटा, पर बेटा बोला, मैंने कुआँ नहीं छुआ।",
                              delivery="dialogue", speaker_name="बेटा")
    assert clone_planner.direct_dialogue(line) == "मैंने कुआँ नहीं छुआ।"


def test_clone_planner_locks_speech_and_uses_simple_references(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGHU_PLANNER", "clone")
    monkeypatch.setenv("RAGHU_MOTION_MODEL", "ltx")
    monkeypatch.setenv("RAGHU_LTX_END_FRAME", "false")
    char_tag = "@CHAR-01-DEV"
    bg_tag = "#BGD-01-OFFICE"
    lines = [
        {"text": "देव ने मेज़ पर गीली चिट्ठी देखी।", "delivery": "narration"},
        {"text": "आपकी चिट्ठी यहाँ है।", "delivery": "dialogue", "speaker_name": "Dev"},
    ] + [{"text": "देव बंद खिड़की की ओर मुड़ा।", "delivery": "narration"}] * 10
    scenes = [{
        "scene_number": i, "background_tag": bg_tag, "character_tags": [char_tag],
        "speaker": char_tag if i == 2 else "NARRATOR",
        "opening": "Dev stands at the desk, letter resting flat.",
        "visual_action": "Dev addresses the unseen sender." if i == 2 else "Dev turns toward the window.",
        "camera": "Locked desk view",
        "ending": "Dev looks toward the closed window.",
    } for i in range(1, 13)]
    responses = iter([
        {"line": "सूखी मेज़ पर एक गीली चिट्ठी पड़ी थी।"},
        {"summary": "Dev discovers a mysterious letter at a locked post office.", "lines": lines},
        {"characters": [{"tag": char_tag, "name": "Dev", "look_summary": "Adult clerk in ochre",
                         "full_prompt": "One proportionate adult clerk in an ochre shirt, inked 2D."}]},
        {"backgrounds": [{"tag": bg_tag, "location_name": "Office", "look_summary": "Desk and closed window",
                          "full_prompt": "An empty post office with a wooden desk and closed window."}]},
        {"scenes": [{**scenes[0], "visual_action": "Dev speaks to the letter."}, *scenes[1:]]},
        {"actions": {"1": scenes[0]["visual_action"]}},
    ])
    prompts = []

    def write(schema, prompt, **kwargs):
        prompts.append(prompt)
        return schema.model_validate(next(responses))

    monkeypatch.setattr(clone_planner.writing, "write", write)
    result = raghu_pipeline.plan(tmp_path, "तीसरी दस्तक", 60, lambda: None)
    assert len(prompts) == 6 and "Dev speaks to the letter" in prompts[-1]
    assert result["shots"][0]["motion"].startswith("Dev turns toward the window.")
    assert [shot["narration"] for shot in result["shots"]] == [line["text"] for line in lines]
    assert len(result["shots"]) == 12 and result["planner"] == "clone"
    _, opening = raghu_pipeline.still_batches(result)
    assert opening[0]["refs"] == ["results/background-BGD-01-OFFICE.png",
                                  "results/character-CHAR-01-DEV.png", "style-wide.jpg"]
    motion = raghu_pipeline.motion_plan(result["shots"])["shots"]
    assert "Keep all mouths closed" in motion[0]["video_prompt"]
    assert "Only this speaker moves" in motion[1]["video_prompt"]
    assert all("ending_image_file" not in shot for shot in motion)
    assert raghu_pipeline.plan(tmp_path, "तीसरी दस्तक", 60, lambda: None) == result
