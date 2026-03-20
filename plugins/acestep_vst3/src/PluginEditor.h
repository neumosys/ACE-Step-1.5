#pragma once

#include <JuceHeader.h>

namespace acestep::vst3
{
class ACEStepVST3AudioProcessor;

class ACEStepVST3AudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit ACEStepVST3AudioProcessorEditor(ACEStepVST3AudioProcessor& processor);
    ~ACEStepVST3AudioProcessorEditor() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

private:
    void syncFromProcessor();
    void updateStatusText();

    ACEStepVST3AudioProcessor& processor_;
    juce::Label titleLabel_;
    juce::Label subtitleLabel_;
    juce::Label statusLabel_;
    juce::Label backendLabel_;
    juce::TextEditor backendEditor_;
    juce::Label noteLabel_;
    juce::TextEditor noteEditor_;
    bool isSyncingFields_ = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ACEStepVST3AudioProcessorEditor)
};
}  // namespace acestep::vst3
