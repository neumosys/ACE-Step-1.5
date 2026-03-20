#include "PluginEditor.h"

#include "PluginProcessor.h"

namespace acestep::vst3
{
namespace
{
constexpr int kEditorWidth = 480;
constexpr int kEditorHeight = 260;
}  // namespace

ACEStepVST3AudioProcessorEditor::ACEStepVST3AudioProcessorEditor(
    ACEStepVST3AudioProcessor& processor)
    : juce::AudioProcessorEditor(&processor), processor_(processor)
{
    setSize(kEditorWidth, kEditorHeight);

    titleLabel_.setText("ACE-Step VST3 Shell", juce::dontSendNotification);
    titleLabel_.setJustificationType(juce::Justification::centredLeft);
    titleLabel_.setFont(juce::Font(20.0f, juce::Font::bold));
    addAndMakeVisible(titleLabel_);

    subtitleLabel_.setText("Placeholder editor. No backend calls or generation logic yet.",
                           juce::dontSendNotification);
    subtitleLabel_.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(subtitleLabel_);

    statusLabel_.setJustificationType(juce::Justification::centredLeft);
    addAndMakeVisible(statusLabel_);

    backendLabel_.setText("Backend URL", juce::dontSendNotification);
    addAndMakeVisible(backendLabel_);

    backendEditor_.setTextToShowWhenEmpty(kDefaultBackendBaseUrl, juce::Colours::grey);
    backendEditor_.setMultiLine(false);
    backendEditor_.setReturnKeyStartsNewLine(false);
    backendEditor_.onTextChange = [this] {
        if (isSyncingFields_)
        {
            return;
        }

        processor_.setBackendBaseUrl(backendEditor_.getText());
        updateStatusText();
    };
    addAndMakeVisible(backendEditor_);

    noteLabel_.setText("Session note", juce::dontSendNotification);
    addAndMakeVisible(noteLabel_);

    noteEditor_.setTextToShowWhenEmpty("Saved with the DAW project", juce::Colours::grey);
    noteEditor_.setMultiLine(false);
    noteEditor_.setReturnKeyStartsNewLine(false);
    noteEditor_.onTextChange = [this] {
        if (isSyncingFields_)
        {
            return;
        }

        processor_.setSessionNote(noteEditor_.getText());
        updateStatusText();
    };
    addAndMakeVisible(noteEditor_);

    syncFromProcessor();
    updateStatusText();
}

ACEStepVST3AudioProcessorEditor::~ACEStepVST3AudioProcessorEditor() = default;

void ACEStepVST3AudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour::fromRGB(18, 22, 32));
}

void ACEStepVST3AudioProcessorEditor::resized()
{
    auto bounds = getLocalBounds().reduced(18);
    auto topRow = bounds.removeFromTop(70);
    titleLabel_.setBounds(topRow.removeFromTop(28));
    subtitleLabel_.setBounds(topRow.removeFromTop(20).translated(0, 4));

    bounds.removeFromTop(6);
    statusLabel_.setBounds(bounds.removeFromTop(24));

    bounds.removeFromTop(12);
    backendLabel_.setBounds(bounds.removeFromTop(20));
    backendEditor_.setBounds(bounds.removeFromTop(28));

    bounds.removeFromTop(10);
    noteLabel_.setBounds(bounds.removeFromTop(20));
    noteEditor_.setBounds(bounds.removeFromTop(28));
}

void ACEStepVST3AudioProcessorEditor::syncFromProcessor()
{
    const auto& state = processor_.getState();
    isSyncingFields_ = true;
    backendEditor_.setText(state.backendBaseUrl, juce::dontSendNotification);
    noteEditor_.setText(state.sessionNote, juce::dontSendNotification);
    isSyncingFields_ = false;
}

void ACEStepVST3AudioProcessorEditor::updateStatusText()
{
    auto status = processor_.getShellStatusText();
    status += "\nState schema version: ";
    status += juce::String(processor_.getState().schemaVersion);
    status += "\nSession note length: ";
    status += juce::String(processor_.getState().sessionNote.length());
    statusLabel_.setText(status, juce::dontSendNotification);
}
}  // namespace acestep::vst3
