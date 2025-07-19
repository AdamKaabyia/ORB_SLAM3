/**
* This file is part of ORB-SLAM3
*
* Headless stub implementation for FrameDrawer - GUI functionality disabled for benchmarking
*/

#include "FrameDrawer.h"
#include "Tracking.h"
#include <opencv2/core/core.hpp>
#include <mutex>

namespace ORB_SLAM3
{

FrameDrawer::FrameDrawer(Atlas* pAtlas) : both(false), mpAtlas(pAtlas)
{
    mState = Tracking::SYSTEM_NOT_READY;
    mIm = cv::Mat(480, 640, CV_8UC3, cv::Scalar(0, 0, 0));
    mImRight = cv::Mat(480, 640, CV_8UC3, cv::Scalar(0, 0, 0));
    N = 0;
    mnTracked = 0;
    mnTrackedVO = 0;
    mbOnlyTracking = false;
}

void FrameDrawer::Update(Tracking *pTracker)
{
    std::unique_lock<std::mutex> lock(mMutex);

    // Update basic state information (essential for core SLAM)
    if(pTracker)
    {
        mState = static_cast<int>(pTracker->mLastProcessedState);

        // Store current frame data without visual processing
        if(pTracker->mLastProcessedState != Tracking::SYSTEM_NOT_READY)
        {
            mCurrentFrame = pTracker->mCurrentFrame;
        }
    }
}

cv::Mat FrameDrawer::DrawFrame(float imageScale)
{
    cv::Mat im;
    {
        std::unique_lock<std::mutex> lock(mMutex);
        // Return empty or basic image for headless operation
        im = cv::Mat(480, 640, CV_8UC3, cv::Scalar(0, 0, 0));
    }
    return im;
}

cv::Mat FrameDrawer::DrawRightFrame(float imageScale)
{
    cv::Mat im;
    {
        std::unique_lock<std::mutex> lock(mMutex);
        // Return empty image for headless operation
        im = cv::Mat(480, 640, CV_8UC3, cv::Scalar(0, 0, 0));
    }
    return im;
}

void FrameDrawer::DrawTextInfo(cv::Mat &im, int nState, cv::Mat &imText)
{
    // Headless implementation - no text drawing needed
}

} // namespace ORB_SLAM3
